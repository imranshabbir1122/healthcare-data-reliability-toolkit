-- SQL Server (UNTESTED). Create watermark, audit and lineage tables if missing.
IF OBJECT_ID('load_watermark', 'U') IS NULL
CREATE TABLE load_watermark (
    table_name VARCHAR(255) PRIMARY KEY,
    last_successful_value VARCHAR(40),
    updated_at VARCHAR(40)
);

IF OBJECT_ID('recon_results', 'U') IS NULL
CREATE TABLE recon_results (
    run_id VARCHAR(64), run_ts VARCHAR(40), source_table VARCHAR(255), target_table VARCHAR(255),
    check_name VARCHAR(255), status VARCHAR(16), source_value VARCHAR(255),
    target_value VARCHAR(255), detail VARCHAR(4000)
);

IF OBJECT_ID('lineage_log', 'U') IS NULL
CREATE TABLE lineage_log (
    step_id VARCHAR(40), run_id VARCHAR(64), seq INT, step_ts VARCHAR(40),
    step_name VARCHAR(255), source VARCHAR(255), target VARCHAR(255),
    transformation VARCHAR(1000), rows_in INT, rows_out INT,
    status VARCHAR(16), error_detail VARCHAR(2000), duration_ms INT,
    toolkit_version VARCHAR(16), note VARCHAR(2000)
);
