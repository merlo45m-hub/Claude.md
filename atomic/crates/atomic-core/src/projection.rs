//! PCA-based 2D projection of embedding vectors.
//!
//! Projects high-dimensional embedding vectors to 2D positions using
//! Principal Component Analysis via power iteration. No external linear
//! algebra crate needed — pure Rust with O(d) working memory.

/// Project a set of embedding vectors to 2D positions.
///
/// Returns `Vec<(atom_id, x, y)>` with coordinates normalized to roughly [-1, 1].
/// Uses power iteration to find the top 2 principal components.
pub fn compute_2d_projection(embeddings: &[(String, Vec<f32>)]) -> Vec<(String, f64, f64)> {
    if embeddings.is_empty() {
        return vec![];
    }
    if embeddings.len() == 1 {
        return vec![(embeddings[0].0.clone(), 0.0, 0.0)];
    }

    // Pick the most common embedding dimension. Mixed dimensions can occur when
    // the user switches embedding models — we project only the majority set and
    // place the rest at the origin so they still appear on the canvas.
    let mut dim_counts: std::collections::HashMap<usize, usize> = std::collections::HashMap::new();
    for (_, emb) in embeddings {
        *dim_counts.entry(emb.len()).or_insert(0) += 1;
    }
    let d = dim_counts
        .iter()
        .max_by_key(|(_, count)| *count)
        .map(|(dim, _)| *dim)
        .unwrap_or(0);
    if d == 0 {
        return embeddings
            .iter()
            .map(|(id, _)| (id.clone(), 0.0, 0.0))
            .collect();
    }

    // Partition into matching and mismatched embeddings.
    let (matching, mismatched): (Vec<_>, Vec<_>) = embeddings
        .iter()
        .cloned()
        .partition(|(_, emb)| emb.len() == d);

    if mismatched.len() > 0 {
        tracing::warn!(
            expected_dim = d,
            mismatched = mismatched.len(),
            "projection: skipping embeddings with non-majority dimension"
        );
    }

    if matching.len() < 2 {
        return embeddings
            .iter()
            .map(|(id, _)| (id.clone(), 0.0, 0.0))
            .collect();
    }

    let embeddings: &[(String, Vec<f32>)] = &matching;
    let n = embeddings.len();

    // Step 1: Compute mean vector
    let mut mean = vec![0.0f64; d];
    for (_, emb) in embeddings {
        for (i, &v) in emb.iter().enumerate() {
            mean[i] += v as f64;
        }
    }
    let inv_n = 1.0 / n as f64;
    for m in mean.iter_mut() {
        *m *= inv_n;
    }

    // Step 2: Power iteration for first eigenvector
    // Computes X^T(Xv) by streaming rows — O(d) working memory
    let eigvec1 = power_iteration(embeddings, &mean, d, None);

    // Step 3: Power iteration for second eigenvector (with deflation)
    let eigvec2 = power_iteration(embeddings, &mean, d, Some(&eigvec1));

    // Step 4: Project all points
    let mut results: Vec<(String, f64, f64)> = Vec::with_capacity(n);
    for (id, emb) in embeddings {
        let mut x = 0.0f64;
        let mut y = 0.0f64;
        for i in 0..d {
            let centered = emb[i] as f64 - mean[i];
            x += centered * eigvec1[i];
            y += centered * eigvec2[i];
        }
        results.push((id.clone(), x, y));
    }

    // Step 5: Normalize to [-1, 1] range
    normalize_positions(&mut results);

    // Append mismatched-dimension atoms at the origin so they remain visible.
    for (id, _) in &mismatched {
        results.push((id.clone(), 0.0, 0.0));
    }

    results
}

/// Power iteration to find the dominant eigenvector of X^T X,
/// where X is the centered data matrix.
///
/// If `deflate_against` is Some, the projection onto that vector is
/// removed at each step (Gram-Schmidt deflation).
fn power_iteration(
    embeddings: &[(String, Vec<f32>)],
    mean: &[f64],
    d: usize,
    deflate_against: Option<&[f64]>,
) -> Vec<f64> {
    let max_iter = 20;

    // Initialize with a deterministic vector (not random — reproducible results)
    let mut v = vec![0.0f64; d];
    for i in 0..d {
        v[i] = ((i as f64 * 0.618033988) % 1.0) - 0.5; // Golden ratio hash
    }
    normalize_vec(&mut v);

    for _ in 0..max_iter {
        // Compute w = X^T (X v) by streaming
        // First pass: compute Xv (n dot products → n scalars)
        // Second pass: accumulate X^T * (Xv) (weighted sum of rows)
        let mut result = vec![0.0f64; d];

        for (_, emb) in embeddings {
            // dot = (row - mean) · v
            let mut dot = 0.0f64;
            for i in 0..d {
                dot += (emb[i] as f64 - mean[i]) * v[i];
            }
            // result += dot * (row - mean)
            for i in 0..d {
                result[i] += dot * (emb[i] as f64 - mean[i]);
            }
        }

        // Deflate: remove component along the first eigenvector
        if let Some(prev) = deflate_against {
            let proj = dot_product(&result, prev);
            for i in 0..d {
                result[i] -= proj * prev[i];
            }
        }

        normalize_vec(&mut result);

        // Check convergence (cosine similarity with previous v)
        let cos = dot_product(&v, &result).abs();
        v = result;

        if cos > 0.999999 {
            break;
        }
    }

    v
}

fn dot_product(a: &[f64], b: &[f64]) -> f64 {
    a.iter().zip(b.iter()).map(|(x, y)| x * y).sum()
}

fn normalize_vec(v: &mut [f64]) {
    let norm: f64 = v.iter().map(|x| x * x).sum::<f64>().sqrt();
    if norm > 1e-10 {
        for x in v.iter_mut() {
            *x /= norm;
        }
    }
}

fn normalize_positions(results: &mut [(String, f64, f64)]) {
    if results.is_empty() {
        return;
    }

    let mut x_min = f64::MAX;
    let mut x_max = f64::MIN;
    let mut y_min = f64::MAX;
    let mut y_max = f64::MIN;

    for (_, x, y) in results.iter() {
        x_min = x_min.min(*x);
        x_max = x_max.max(*x);
        y_min = y_min.min(*y);
        y_max = y_max.max(*y);
    }

    let x_range = (x_max - x_min).max(1e-10);
    let y_range = (y_max - y_min).max(1e-10);

    for (_, x, y) in results.iter_mut() {
        *x = (*x - x_min) / x_range * 2.0 - 1.0;
        *y = (*y - y_min) / y_range * 2.0 - 1.0;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_empty() {
        let result = compute_2d_projection(&[]);
        assert!(result.is_empty());
    }

    #[test]
    fn test_single_atom() {
        let result = compute_2d_projection(&[("a1".to_string(), vec![1.0, 2.0, 3.0])]);
        assert_eq!(result.len(), 1);
        assert_eq!(result[0].0, "a1");
        assert_eq!(result[0].1, 0.0);
        assert_eq!(result[0].2, 0.0);
    }

    #[test]
    fn test_two_atoms() {
        let result = compute_2d_projection(&[
            ("a1".to_string(), vec![1.0, 0.0, 0.0]),
            ("a2".to_string(), vec![0.0, 1.0, 0.0]),
        ]);
        assert_eq!(result.len(), 2);
        // They should be separated
        let dist =
            ((result[0].1 - result[1].1).powi(2) + (result[0].2 - result[1].2).powi(2)).sqrt();
        assert!(dist > 0.1, "atoms should be separated, got dist={}", dist);
    }

    #[test]
    fn test_clusters_separate() {
        // Two tight clusters in different directions
        let mut embeddings = Vec::new();
        for i in 0..10 {
            let noise = i as f32 * 0.01;
            embeddings.push((format!("cluster_a_{}", i), vec![1.0 + noise, 0.0, 0.0, 0.0]));
        }
        for i in 0..10 {
            let noise = i as f32 * 0.01;
            embeddings.push((format!("cluster_b_{}", i), vec![0.0, 0.0, 1.0 + noise, 0.0]));
        }

        let result = compute_2d_projection(&embeddings);
        assert_eq!(result.len(), 20);

        // Compute centroid of each cluster
        let (mut ax, mut ay) = (0.0, 0.0);
        let (mut bx, mut by) = (0.0, 0.0);
        for (id, x, y) in &result {
            if id.starts_with("cluster_a") {
                ax += x;
                ay += y;
            } else {
                bx += x;
                by += y;
            }
        }
        ax /= 10.0;
        ay /= 10.0;
        bx /= 10.0;
        by /= 10.0;

        let cluster_dist = ((ax - bx).powi(2) + (ay - by).powi(2)).sqrt();
        assert!(
            cluster_dist > 0.5,
            "clusters should be well separated, got dist={}",
            cluster_dist
        );
    }

    #[test]
    fn test_deterministic() {
        let embeddings: Vec<(String, Vec<f32>)> = (0..5)
            .map(|i| {
                (
                    format!("a{}", i),
                    vec![i as f32, (i * 2) as f32, (i * 3) as f32],
                )
            })
            .collect();

        let r1 = compute_2d_projection(&embeddings);
        let r2 = compute_2d_projection(&embeddings);

        for i in 0..r1.len() {
            assert_eq!(r1[i].0, r2[i].0);
            assert!(
                (r1[i].1 - r2[i].1).abs() < 1e-10,
                "x should be deterministic"
            );
            assert!(
                (r1[i].2 - r2[i].2).abs() < 1e-10,
                "y should be deterministic"
            );
        }
    }
}
