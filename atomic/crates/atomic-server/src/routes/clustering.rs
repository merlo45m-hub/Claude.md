//! Clustering routes

use crate::db_extractor::Db;
use crate::error::ok_or_error;
use actix_web::{web, HttpResponse};
use serde::{Deserialize, Serialize};
use utoipa::{IntoParams, ToSchema};

#[derive(Deserialize, Serialize, ToSchema)]
pub struct ComputeClustersBody {
    /// Minimum similarity for clustering (default: 0.6)
    pub min_similarity: Option<f32>,
    /// Minimum cluster size (default: 2)
    pub min_cluster_size: Option<i32>,
}

#[utoipa::path(post, path = "/api/clustering/compute", request_body = ComputeClustersBody, responses((status = 200, description = "Computed clusters", body = Vec<atomic_core::AtomCluster>)), tag = "clustering")]
pub async fn compute_clusters(db: Db, body: web::Json<ComputeClustersBody>) -> HttpResponse {
    let min_similarity = body.min_similarity.unwrap_or(0.6);
    let min_cluster_size = body.min_cluster_size.unwrap_or(2);
    let core = &db.0;
    let clusters = match core
        .compute_clusters(min_similarity, min_cluster_size)
        .await
    {
        Ok(c) => c,
        Err(e) => return crate::error::error_response(e),
    };
    match core.save_clusters(&clusters).await {
        Ok(()) => HttpResponse::Ok().json(clusters),
        Err(e) => crate::error::error_response(e),
    }
}

#[utoipa::path(get, path = "/api/clustering", responses((status = 200, description = "Saved clusters", body = Vec<atomic_core::AtomCluster>)), tag = "clustering")]
pub async fn get_clusters(db: Db) -> HttpResponse {
    ok_or_error(db.0.get_clusters().await)
}

#[derive(Deserialize, IntoParams)]
#[into_params(parameter_in = Query)]
pub struct ConnectionCountsQuery {
    /// Minimum similarity (default: 0.5)
    pub min_similarity: Option<f32>,
}

#[utoipa::path(get, path = "/api/clustering/connection-counts", params(ConnectionCountsQuery), responses((status = 200, description = "Connection counts per atom")), tag = "clustering")]
pub async fn get_connection_counts(
    db: Db,
    query: web::Query<ConnectionCountsQuery>,
) -> HttpResponse {
    let min_similarity = query.min_similarity.unwrap_or(0.5);
    ok_or_error(db.0.get_connection_counts(min_similarity).await)
}
