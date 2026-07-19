//! Log export endpoint

use crate::state::AppState;
use actix_web::{web, HttpResponse};
use serde::Serialize;
use utoipa::ToSchema;

#[derive(Serialize, ToSchema)]
pub struct LogsResponse {
    pub logs: String,
}

#[utoipa::path(
    get,
    path = "/api/logs",
    responses(
        (status = 200, description = "Recent in-memory server log lines", body = LogsResponse)
    ),
    tag = "logs"
)]
pub async fn get_logs(state: web::Data<AppState>) -> HttpResponse {
    let logs = state.log_buffer.dump();
    HttpResponse::Ok().json(LogsResponse { logs })
}
