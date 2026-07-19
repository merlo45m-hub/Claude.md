use std::collections::{BTreeMap, HashMap, HashSet};
use std::path::Path;
use std::time::Instant;

use anyhow::{anyhow, bail, Context, Result};
use atomic_core::{AtomicCore, CreateAtomRequest, EmbeddingEvent, SearchMode, SearchOptions};
use serde::Deserialize;
use serde_json::Value;
use tempfile::TempDir;
use tokio::sync::mpsc::UnboundedReceiver;

use crate::dataset::BenchDataset;
use crate::mock_ai::MockAiServer;
use crate::report::{JsonlReporter, MetricRecord, RunContext};
use crate::runner::{BenchAiConfig, BenchProvider, BenchSampleStrategy};

type EventRx = UnboundedReceiver<EmbeddingEvent>;

#[derive(Debug, Clone)]
pub struct LongMemEvalDataset {
    pub id: String,
    pub instances: Vec<LongMemEvalInstance>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct LongMemEvalInstance {
    pub question_id: String,
    pub question_type: String,
    pub question: String,
    pub answer: Value,
    #[serde(default)]
    pub question_date: Option<String>,
    #[serde(default)]
    pub haystack_session_ids: Vec<String>,
    #[serde(default)]
    pub haystack_dates: Vec<String>,
    #[serde(default)]
    pub haystack_sessions: Vec<Vec<LongMemEvalTurn>>,
    #[serde(default)]
    pub answer_session_ids: Vec<String>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct LongMemEvalTurn {
    pub role: String,
    pub content: String,
    #[serde(default)]
    pub has_answer: Option<bool>,
}

impl LongMemEvalDataset {
    pub fn load(path: impl AsRef<Path>) -> Result<Self> {
        let path = path.as_ref();
        let file = std::fs::File::open(path).with_context(|| format!("open {}", path.display()))?;
        let instances: Vec<LongMemEvalInstance> =
            serde_json::from_reader(file).with_context(|| format!("parse {}", path.display()))?;
        let id = path
            .file_stem()
            .and_then(|s| s.to_str())
            .unwrap_or("longmemeval")
            .to_string();
        Ok(Self { id, instances })
    }
}

pub async fn run(
    ctx: &RunContext,
    dataset: &BenchDataset,
    reporter: &mut JsonlReporter,
) -> Result<()> {
    super::scaffold::emit_scaffold(
        ctx,
        dataset,
        reporter,
        "personal_memory",
        &[
            "memory.fact_recall",
            "memory.temporal_reasoning_accuracy",
            "memory.knowledge_update_accuracy",
            "memory.multi_note_reasoning_accuracy",
            "memory.abstention_accuracy",
            "memory.context_tokens_per_query",
            "longmemeval.evidence_session_recall_at_k",
            "longmemeval.evidence_session_mrr",
        ],
    )
}

fn select_instances<'a>(
    dataset: &'a LongMemEvalDataset,
    limit: Option<usize>,
    strategy: BenchSampleStrategy,
) -> Vec<&'a LongMemEvalInstance> {
    let target = limit
        .unwrap_or(dataset.instances.len())
        .min(dataset.instances.len());
    match strategy {
        BenchSampleStrategy::First => dataset.instances.iter().take(target).collect(),
        BenchSampleStrategy::Stratified => {
            let mut groups: BTreeMap<String, Vec<&LongMemEvalInstance>> = BTreeMap::new();
            for instance in &dataset.instances {
                groups
                    .entry(instance.sample_group())
                    .or_default()
                    .push(instance);
            }

            let mut selected = Vec::with_capacity(target);
            let mut index = 0usize;
            while selected.len() < target {
                let mut added = false;
                for group in groups.values() {
                    if let Some(instance) = group.get(index) {
                        selected.push(*instance);
                        added = true;
                        if selected.len() == target {
                            break;
                        }
                    }
                }
                if !added {
                    break;
                }
                index += 1;
            }
            selected
        }
    }
}

fn emit_sample_group_metrics(
    ctx: &RunContext,
    reporter: &mut JsonlReporter,
    instances: &[&LongMemEvalInstance],
) -> Result<()> {
    let mut counts: BTreeMap<String, usize> = BTreeMap::new();
    for instance in instances {
        *counts.entry(instance.sample_group()).or_default() += 1;
    }

    reporter.emit(&MetricRecord::new(
        ctx,
        "longmemeval.sample_groups_total",
        counts.len() as f64,
        "count",
    ))?;
    for (group, count) in counts {
        reporter.emit(
            &MetricRecord::new(
                ctx,
                "longmemeval.sample_group_instances_total",
                count as f64,
                "count",
            )
            .with_label("group", group),
        )?;
    }
    Ok(())
}

pub async fn run_longmemeval(
    ctx: &RunContext,
    dataset: &LongMemEvalDataset,
    reporter: &mut JsonlReporter,
    keep_db: bool,
    limit: Option<usize>,
    top_k: usize,
    sample_strategy: BenchSampleStrategy,
    ai_config: &BenchAiConfig,
) -> Result<()> {
    let top_k = top_k.max(1);
    let search_k = top_k.max(5);
    let run_start = Instant::now();
    let ai = BenchAiRuntime::start(ai_config).await?;
    let instances = select_instances(dataset, limit, sample_strategy);

    reporter.emit(&MetricRecord::new(
        ctx,
        "longmemeval.instances_total",
        instances.len() as f64,
        "count",
    ))?;
    reporter.emit(
        &MetricRecord::new(
            ctx,
            "longmemeval.sample_stratified_enabled",
            if sample_strategy == BenchSampleStrategy::Stratified {
                1.0
            } else {
                0.0
            },
            "bool",
        )
        .with_label("strategy", sample_strategy.label()),
    )?;
    emit_sample_group_metrics(ctx, reporter, &instances)?;

    let mut non_abstention_count = 0usize;
    let mut abstention_count = 0usize;
    let mut recall_sum = 0.0f64;
    let mut hit_sum = 0.0f64;
    let mut mrr_sum = 0.0f64;
    let mut recall_at_5_sum = 0.0f64;
    let mut hit_at_5_sum = 0.0f64;
    let mut mrr_at_5_sum = 0.0f64;
    let mut sessions_ingested = 0usize;

    for instance in instances {
        let result = run_instance(ctx, instance, reporter, &ai, keep_db, top_k, search_k).await?;
        sessions_ingested += result.sessions_ingested;

        if instance.is_abstention() {
            abstention_count += 1;
        } else {
            non_abstention_count += 1;
            recall_sum += result.recall_at_k;
            hit_sum += if result.hit_at_k { 1.0 } else { 0.0 };
            mrr_sum += result.mrr;
            recall_at_5_sum += result.recall_at_5;
            hit_at_5_sum += if result.hit_at_5 { 1.0 } else { 0.0 };
            mrr_at_5_sum += result.mrr_at_5;
        }
    }

    let denom = non_abstention_count.max(1) as f64;
    reporter.emit(&MetricRecord::new(
        ctx,
        "longmemeval.non_abstention_questions_total",
        non_abstention_count as f64,
        "count",
    ))?;
    reporter.emit(&MetricRecord::new(
        ctx,
        "longmemeval.abstention_questions_total",
        abstention_count as f64,
        "count",
    ))?;
    reporter.emit(&MetricRecord::new(
        ctx,
        "longmemeval.sessions_ingested_total",
        sessions_ingested as f64,
        "count",
    ))?;
    reporter.emit(
        &MetricRecord::new(
            ctx,
            "longmemeval.evidence_session_recall_at_k_mean",
            recall_sum / denom,
            "ratio",
        )
        .with_label("k", top_k.to_string()),
    )?;
    reporter.emit(
        &MetricRecord::new(
            ctx,
            "longmemeval.evidence_session_hit_at_k_rate",
            hit_sum / denom,
            "ratio",
        )
        .with_label("k", top_k.to_string()),
    )?;
    reporter.emit(
        &MetricRecord::new(
            ctx,
            "longmemeval.evidence_session_mrr_mean",
            mrr_sum / denom,
            "ratio",
        )
        .with_label("k", top_k.to_string()),
    )?;
    reporter.emit(&MetricRecord::new(
        ctx,
        "longmemeval.evidence_session_recall_at_5_mean",
        recall_at_5_sum / denom,
        "ratio",
    ))?;
    reporter.emit(&MetricRecord::new(
        ctx,
        "longmemeval.evidence_session_hit_at_5_rate",
        hit_at_5_sum / denom,
        "ratio",
    ))?;
    reporter.emit(&MetricRecord::new(
        ctx,
        "longmemeval.evidence_session_mrr_at_5_mean",
        mrr_at_5_sum / denom,
        "ratio",
    ))?;
    ai.emit_provider_metrics(ctx, reporter)?;
    reporter.emit(&MetricRecord::new(
        ctx,
        "run.duration_ms",
        run_start.elapsed().as_secs_f64() * 1000.0,
        "ms",
    ))?;
    Ok(())
}

struct InstanceResult {
    sessions_ingested: usize,
    recall_at_k: f64,
    hit_at_k: bool,
    mrr: f64,
    recall_at_5: f64,
    hit_at_5: bool,
    mrr_at_5: f64,
}

struct RetrievedSession {
    session_id: String,
    rank: usize,
    score: f32,
}

struct RetrievalScore {
    retrieved_evidence: usize,
    recall: f64,
    hit: bool,
    mrr: f64,
    first_rank: Option<usize>,
}

fn score_retrieval(
    retrieved_sessions: &[RetrievedSession],
    evidence: &HashSet<&str>,
    cutoff: usize,
) -> RetrievalScore {
    let retrieved_evidence = retrieved_sessions
        .iter()
        .filter(|session| session.rank <= cutoff && evidence.contains(session.session_id.as_str()))
        .count();
    let recall = if evidence.is_empty() {
        0.0
    } else {
        retrieved_evidence as f64 / evidence.len() as f64
    };
    let first_rank = retrieved_sessions
        .iter()
        .filter(|session| session.rank <= cutoff)
        .find(|session| evidence.contains(session.session_id.as_str()))
        .map(|session| session.rank);
    let mrr = first_rank.map(|rank| 1.0 / rank as f64).unwrap_or(0.0);

    RetrievalScore {
        retrieved_evidence,
        recall,
        hit: first_rank.is_some(),
        mrr,
        first_rank,
    }
}

fn emit_retrieval_detail_metrics(
    ctx: &RunContext,
    reporter: &mut JsonlReporter,
    instance: &LongMemEvalInstance,
    retrieved_sessions: &[RetrievedSession],
    evidence: &HashSet<&str>,
    top_k: usize,
) -> Result<()> {
    let score_at_k = score_retrieval(retrieved_sessions, evidence, top_k);
    let score_at_5 = score_retrieval(retrieved_sessions, evidence, 5);

    reporter.emit(
        &MetricRecord::new(
            ctx,
            "longmemeval.evidence_sessions_total",
            evidence.len() as f64,
            "count",
        )
        .with_label("question_id", &instance.question_id)
        .with_label("question_type", &instance.question_type)
        .with_label("abstention", instance.is_abstention().to_string()),
    )?;
    reporter.emit(
        &MetricRecord::new(
            ctx,
            "longmemeval.retrieved_sessions_total",
            retrieved_sessions.len() as f64,
            "count",
        )
        .with_label("question_id", &instance.question_id)
        .with_label("question_type", &instance.question_type),
    )?;
    reporter.emit(
        &MetricRecord::new(
            ctx,
            "longmemeval.evidence_sessions_retrieved_at_k",
            score_at_k.retrieved_evidence as f64,
            "count",
        )
        .with_label("question_id", &instance.question_id)
        .with_label("question_type", &instance.question_type)
        .with_label("k", top_k.to_string()),
    )?;
    reporter.emit(
        &MetricRecord::new(
            ctx,
            "longmemeval.evidence_sessions_retrieved_at_5",
            score_at_5.retrieved_evidence as f64,
            "count",
        )
        .with_label("question_id", &instance.question_id)
        .with_label("question_type", &instance.question_type),
    )?;
    reporter.emit(
        &MetricRecord::new(
            ctx,
            "longmemeval.first_evidence_rank",
            score_at_k.first_rank.unwrap_or(0) as f64,
            "rank",
        )
        .with_label("question_id", &instance.question_id)
        .with_label("question_type", &instance.question_type)
        .with_label("k", top_k.to_string()),
    )?;

    let mut rank_by_session = HashMap::new();
    for session in retrieved_sessions {
        let is_evidence = evidence.contains(session.session_id.as_str());
        rank_by_session.insert(session.session_id.as_str(), session.rank);
        reporter.emit(
            &MetricRecord::new(
                ctx,
                "longmemeval.retrieved_session_rank",
                session.rank as f64,
                "rank",
            )
            .with_label("question_id", &instance.question_id)
            .with_label("question_type", &instance.question_type)
            .with_label("session_id", &session.session_id)
            .with_label("is_evidence", is_evidence.to_string()),
        )?;
        reporter.emit(
            &MetricRecord::new(
                ctx,
                "longmemeval.retrieved_session_score",
                session.score as f64,
                "score",
            )
            .with_label("question_id", &instance.question_id)
            .with_label("question_type", &instance.question_type)
            .with_label("session_id", &session.session_id)
            .with_label("rank", session.rank.to_string())
            .with_label("is_evidence", is_evidence.to_string()),
        )?;
    }

    for evidence_session_id in evidence {
        reporter.emit(
            &MetricRecord::new(
                ctx,
                "longmemeval.evidence_session_rank",
                rank_by_session
                    .get(evidence_session_id)
                    .copied()
                    .unwrap_or(0) as f64,
                "rank",
            )
            .with_label("question_id", &instance.question_id)
            .with_label("question_type", &instance.question_type)
            .with_label("session_id", *evidence_session_id)
            .with_label("k", top_k.to_string()),
        )?;
    }

    Ok(())
}

enum BenchAiRuntime {
    Mock(MockAiServer),
    OpenRouter {
        api_key: String,
        embedding_model: String,
        tagging_model: String,
        enable_auto_tagging: bool,
    },
}

impl BenchAiRuntime {
    async fn start(config: &BenchAiConfig) -> Result<Self> {
        match config.provider {
            BenchProvider::Mock => Ok(Self::Mock(MockAiServer::start().await)),
            BenchProvider::OpenRouter => {
                let api_key = config
                    .openrouter_api_key
                    .clone()
                    .filter(|key| !key.trim().is_empty())
                    .ok_or_else(|| {
                        anyhow!(
                            "OpenRouter provider requires --openrouter-api-key or OPENROUTER_API_KEY"
                        )
                    })?;
                Ok(Self::OpenRouter {
                    api_key,
                    embedding_model: config.embedding_model.clone(),
                    tagging_model: config.tagging_model.clone(),
                    enable_auto_tagging: config.enable_auto_tagging,
                })
            }
        }
    }

    fn emit_provider_metrics(&self, ctx: &RunContext, reporter: &mut JsonlReporter) -> Result<()> {
        match self {
            Self::Mock(mock) => {
                reporter.emit(&MetricRecord::new(
                    ctx,
                    "provider.embedding_requests_total",
                    mock.embedding_request_count() as f64,
                    "count",
                ))?;
                reporter.emit(&MetricRecord::new(
                    ctx,
                    "provider.chat_requests_total",
                    mock.chat_request_count() as f64,
                    "count",
                ))?;
            }
            Self::OpenRouter {
                enable_auto_tagging,
                ..
            } => {
                reporter.emit(&MetricRecord::new(
                    ctx,
                    "provider.openrouter_enabled",
                    1.0,
                    "bool",
                ))?;
                reporter.emit(&MetricRecord::new(
                    ctx,
                    "provider.auto_tagging_enabled",
                    if *enable_auto_tagging { 1.0 } else { 0.0 },
                    "bool",
                ))?;
            }
        }
        Ok(())
    }
}

async fn run_instance(
    ctx: &RunContext,
    instance: &LongMemEvalInstance,
    reporter: &mut JsonlReporter,
    ai: &BenchAiRuntime,
    keep_db: bool,
    top_k: usize,
    search_k: usize,
) -> Result<InstanceResult> {
    let instance_start = Instant::now();
    let tempdir = TempDir::new().context("create LongMemEval tempdir")?;
    let db_path = tempdir.path().join(format!(
        "{}.db",
        sanitize_path_component(&instance.question_id)
    ));
    let core = AtomicCore::open_or_create(&db_path).context("open LongMemEval database")?;
    configure_core(&core, ai).await?;

    let mut atom_to_session = HashMap::new();
    let ingest_start = Instant::now();
    let mut requests = Vec::new();
    let mut source_to_session = HashMap::new();

    for (idx, turns) in instance.haystack_sessions.iter().enumerate() {
        if turns.is_empty() {
            continue;
        }
        let session_id = instance
            .haystack_session_ids
            .get(idx)
            .cloned()
            .unwrap_or_else(|| format!("session-{idx}"));
        let session_date = instance.haystack_dates.get(idx).cloned();
        let content = render_session_atom(instance, &session_id, session_date.as_deref(), turns);
        let source_url = format!(
            "bench://longmemeval/{}/{}",
            instance.question_id, session_id
        );
        source_to_session.insert(source_url.clone(), session_id);
        requests.push(CreateAtomRequest {
            content,
            source_url: Some(source_url),
            published_at: session_date,
            ..Default::default()
        });
    }

    let sessions_ingested = requests.len();
    if !requests.is_empty() {
        let (on_event, mut rx) = event_collector();
        let created = core
            .create_atoms_bulk(requests, on_event)
            .await
            .context("bulk create LongMemEval session atoms")?;
        if created.skipped > 0 {
            bail!(
                "LongMemEval bulk import unexpectedly skipped {} session atoms",
                created.skipped
            );
        }

        let created_atom_ids: Vec<String> = created
            .atoms
            .iter()
            .map(|created| created.atom.id.clone())
            .collect();
        for created in created.atoms {
            let source_url = created.atom.source_url.as_deref().ok_or_else(|| {
                anyhow!(
                    "LongMemEval session atom {} missing source URL",
                    created.atom.id
                )
            })?;
            let session_id = source_to_session
                .get(source_url)
                .cloned()
                .ok_or_else(|| anyhow!("unknown LongMemEval source URL: {source_url}"))?;
            atom_to_session.insert(created.atom.id, session_id);
        }
        await_pipeline_many(&mut rx, &created_atom_ids).await?;
    }

    reporter.emit(
        &MetricRecord::new(
            ctx,
            "longmemeval.instance_ingest_ms",
            ingest_start.elapsed().as_secs_f64() * 1000.0,
            "ms",
        )
        .with_label("question_id", &instance.question_id)
        .with_label("question_type", &instance.question_type),
    )?;

    let search_start = Instant::now();
    let results = core
        .search(
            SearchOptions::new(&instance.question, SearchMode::Hybrid, search_k as i32)
                .with_threshold(0.0),
        )
        .await
        .context("search LongMemEval memory")?;
    reporter.emit(
        &MetricRecord::new(
            ctx,
            "longmemeval.instance_search_ms",
            search_start.elapsed().as_secs_f64() * 1000.0,
            "ms",
        )
        .with_label("question_id", &instance.question_id)
        .with_label("question_type", &instance.question_type),
    )?;

    let retrieved_sessions: Vec<RetrievedSession> = results
        .iter()
        .enumerate()
        .filter_map(|(idx, result)| {
            atom_to_session
                .get(&result.atom.atom.id)
                .cloned()
                .map(|session_id| RetrievedSession {
                    session_id,
                    rank: idx + 1,
                    score: result.similarity_score,
                })
        })
        .collect();
    let evidence: HashSet<&str> = instance
        .answer_session_ids
        .iter()
        .map(String::as_str)
        .collect();
    let scoring_at_k = score_retrieval(&retrieved_sessions, &evidence, top_k);
    let scoring_at_5 = score_retrieval(&retrieved_sessions, &evidence, 5);

    emit_retrieval_detail_metrics(
        ctx,
        reporter,
        instance,
        &retrieved_sessions,
        &evidence,
        top_k,
    )?;

    reporter.emit(
        &MetricRecord::new(
            ctx,
            "longmemeval.evidence_session_recall_at_k",
            scoring_at_k.recall,
            "ratio",
        )
        .with_label("question_id", &instance.question_id)
        .with_label("question_type", &instance.question_type)
        .with_label("abstention", instance.is_abstention().to_string())
        .with_label("k", top_k.to_string()),
    )?;
    reporter.emit(
        &MetricRecord::new(
            ctx,
            "longmemeval.evidence_session_hit_at_k",
            if scoring_at_k.hit { 1.0 } else { 0.0 },
            "bool",
        )
        .with_label("question_id", &instance.question_id)
        .with_label("question_type", &instance.question_type)
        .with_label("abstention", instance.is_abstention().to_string())
        .with_label("k", top_k.to_string()),
    )?;
    reporter.emit(
        &MetricRecord::new(
            ctx,
            "longmemeval.evidence_session_mrr",
            scoring_at_k.mrr,
            "ratio",
        )
        .with_label("question_id", &instance.question_id)
        .with_label("question_type", &instance.question_type)
        .with_label("abstention", instance.is_abstention().to_string())
        .with_label("k", top_k.to_string()),
    )?;
    reporter.emit(
        &MetricRecord::new(
            ctx,
            "longmemeval.evidence_session_recall_at_5",
            scoring_at_5.recall,
            "ratio",
        )
        .with_label("question_id", &instance.question_id)
        .with_label("question_type", &instance.question_type)
        .with_label("abstention", instance.is_abstention().to_string()),
    )?;
    reporter.emit(
        &MetricRecord::new(
            ctx,
            "longmemeval.evidence_session_hit_at_5",
            if scoring_at_5.hit { 1.0 } else { 0.0 },
            "bool",
        )
        .with_label("question_id", &instance.question_id)
        .with_label("question_type", &instance.question_type)
        .with_label("abstention", instance.is_abstention().to_string()),
    )?;
    reporter.emit(
        &MetricRecord::new(
            ctx,
            "longmemeval.evidence_session_mrr_at_5",
            scoring_at_5.mrr,
            "ratio",
        )
        .with_label("question_id", &instance.question_id)
        .with_label("question_type", &instance.question_type)
        .with_label("abstention", instance.is_abstention().to_string()),
    )?;
    reporter.emit(
        &MetricRecord::new(
            ctx,
            "longmemeval.instance_duration_ms",
            instance_start.elapsed().as_secs_f64() * 1000.0,
            "ms",
        )
        .with_label("question_id", &instance.question_id)
        .with_label("question_type", &instance.question_type),
    )?;

    if keep_db {
        reporter.emit(
            &MetricRecord::new(ctx, "run.kept_database", 1.0, "bool")
                .with_label("question_id", &instance.question_id)
                .with_label("path", db_path.display().to_string()),
        )?;
        std::mem::forget(tempdir);
    }

    Ok(InstanceResult {
        sessions_ingested,
        recall_at_k: scoring_at_k.recall,
        hit_at_k: scoring_at_k.hit,
        mrr: scoring_at_k.mrr,
        recall_at_5: scoring_at_5.recall,
        hit_at_5: scoring_at_5.hit,
        mrr_at_5: scoring_at_5.mrr,
    })
}

impl LongMemEvalInstance {
    fn is_abstention(&self) -> bool {
        self.question_id.ends_with("_abs")
    }

    fn sample_group(&self) -> String {
        if self.is_abstention() {
            format!("{}::abstention", self.question_type)
        } else {
            self.question_type.clone()
        }
    }
}

async fn configure_core(core: &AtomicCore, ai: &BenchAiRuntime) -> Result<()> {
    match ai {
        BenchAiRuntime::Mock(mock) => {
            let mock_url = mock.base_url();
            for (key, value) in [
                ("provider", "openai_compat"),
                ("openai_compat_base_url", mock_url.as_str()),
                ("openai_compat_api_key", "atomic-bench"),
                ("openai_compat_embedding_model", "mock-embed"),
                ("openai_compat_llm_model", "mock-llm"),
                ("openai_compat_embedding_dimension", "1536"),
                ("auto_tagging_enabled", "false"),
            ] {
                core.set_setting(key, value).await?;
            }
        }
        BenchAiRuntime::OpenRouter {
            api_key,
            embedding_model,
            tagging_model,
            enable_auto_tagging,
        } => {
            if embedding_model.trim().is_empty() {
                bail!("embedding model cannot be empty");
            }
            if tagging_model.trim().is_empty() {
                bail!("tagging model cannot be empty");
            }
            for (key, value) in [
                ("provider", "openrouter"),
                ("openrouter_api_key", api_key.as_str()),
                ("embedding_model", embedding_model.as_str()),
                ("tagging_model", tagging_model.as_str()),
                (
                    "auto_tagging_enabled",
                    if *enable_auto_tagging {
                        "true"
                    } else {
                        "false"
                    },
                ),
            ] {
                core.set_setting(key, value).await?;
            }
            if *enable_auto_tagging {
                core.configure_autotag_targets(
                    &[
                        "Topics".to_string(),
                        "People".to_string(),
                        "Locations".to_string(),
                        "Organizations".to_string(),
                        "Events".to_string(),
                    ],
                    &[],
                )
                .await?;
            }
        }
    }
    Ok(())
}

fn render_session_atom(
    instance: &LongMemEvalInstance,
    session_id: &str,
    session_date: Option<&str>,
    turns: &[LongMemEvalTurn],
) -> String {
    let mut content = format!(
        "# LongMemEval Session {}\n\nQuestion ID: {}\nQuestion date: {}\nSession date: {}\n\n",
        session_id,
        instance.question_id,
        instance.question_date.as_deref().unwrap_or("unknown"),
        session_date.unwrap_or("unknown"),
    );
    for turn in turns {
        if turn.has_answer.unwrap_or(false) {
            content.push_str("Evidence turn: true\n\n");
        }
        content.push_str(&format!("## {}\n\n{}\n\n", turn.role, turn.content.trim()));
    }
    content
}

fn event_collector() -> (
    impl Fn(EmbeddingEvent) + Send + Sync + Clone + 'static,
    EventRx,
) {
    let (tx, rx) = tokio::sync::mpsc::unbounded_channel();
    let tx = std::sync::Arc::new(tx);
    let cb = move |event| {
        let _ = tx.send(event);
    };
    (cb, rx)
}

async fn await_pipeline_many(rx: &mut EventRx, atom_ids: &[String]) -> Result<()> {
    if atom_ids.is_empty() {
        return Ok(());
    }

    let expected: HashSet<&str> = atom_ids.iter().map(String::as_str).collect();
    let mut embedding_done: HashSet<String> = HashSet::new();
    let mut tagging_done: HashSet<String> = HashSet::new();
    let deadline = tokio::time::Instant::now() + std::time::Duration::from_secs(120);

    while embedding_done.len() < expected.len() || tagging_done.len() < expected.len() {
        let remaining = deadline.saturating_duration_since(tokio::time::Instant::now());
        if remaining.is_zero() {
            let missing_embeddings = expected.len().saturating_sub(embedding_done.len());
            let missing_tagging = expected.len().saturating_sub(tagging_done.len());
            return Err(anyhow!(
                "pipeline timed out for LongMemEval bulk import: {missing_embeddings} embeddings and {missing_tagging} tagging jobs still pending"
            ));
        }

        let event = tokio::time::timeout(remaining, rx.recv())
            .await
            .context("wait for bulk pipeline event")?
            .ok_or_else(|| {
                anyhow!("pipeline event channel closed during LongMemEval bulk import")
            })?;

        match event {
            EmbeddingEvent::EmbeddingComplete { atom_id }
                if expected.contains(atom_id.as_str()) =>
            {
                embedding_done.insert(atom_id);
            }
            EmbeddingEvent::EmbeddingFailed { atom_id, error }
                if expected.contains(atom_id.as_str()) =>
            {
                return Err(anyhow!("embedding failed for atom {atom_id}: {error}"));
            }
            EmbeddingEvent::TaggingComplete { atom_id, .. }
            | EmbeddingEvent::TaggingSkipped { atom_id }
                if expected.contains(atom_id.as_str()) =>
            {
                tagging_done.insert(atom_id);
            }
            EmbeddingEvent::TaggingFailed { atom_id, error }
                if expected.contains(atom_id.as_str()) =>
            {
                return Err(anyhow!("tagging failed for atom {atom_id}: {error}"));
            }
            _ => {}
        }
    }

    Ok(())
}

fn sanitize_path_component(value: &str) -> String {
    value
        .chars()
        .map(|ch| {
            if ch.is_ascii_alphanumeric() || ch == '-' || ch == '_' {
                ch
            } else {
                '_'
            }
        })
        .collect()
}
