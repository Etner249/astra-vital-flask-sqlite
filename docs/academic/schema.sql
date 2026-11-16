-- Real schema extracted from the SQLite database created by `flask bootstrap` (SQLAlchemy create_all)
PRAGMA foreign_keys=ON;

CREATE TABLE api_tokens (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	token_hash VARCHAR(64) NOT NULL, 
	created_at DATETIME NOT NULL, 
	expires_at DATETIME NOT NULL, 
	revoked_at DATETIME, 
	last_used_at DATETIME, 
	CONSTRAINT pk_api_tokens PRIMARY KEY (id), 
	CONSTRAINT fk_api_tokens_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	CONSTRAINT uq_api_tokens_token_hash UNIQUE (token_hash)
);

CREATE TABLE astronauts (
	id INTEGER NOT NULL, 
	code VARCHAR(30) NOT NULL, 
	full_name VARCHAR(120) NOT NULL, 
	demo_age INTEGER, 
	role_on_board VARCHAR(60), 
	mission_id INTEGER, 
	status VARCHAR(20) NOT NULL, 
	notes TEXT, 
	is_synthetic BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	CONSTRAINT pk_astronauts PRIMARY KEY (id), 
	CONSTRAINT ck_astronauts_age_range CHECK (demo_age IS NULL OR demo_age BETWEEN 18 AND 80), 
	CONSTRAINT ck_astronauts_status_valid CHECK (status IN ('active','inactive','returned')), 
	CONSTRAINT fk_astronauts_mission_id_missions FOREIGN KEY(mission_id) REFERENCES missions (id) ON DELETE RESTRICT
);

CREATE TABLE audit_logs (
	id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	user_id INTEGER, 
	action VARCHAR(20) NOT NULL, 
	entity VARCHAR(40) NOT NULL, 
	entity_id INTEGER, 
	details TEXT, 
	ip_address VARCHAR(45), 
	CONSTRAINT pk_audit_logs PRIMARY KEY (id), 
	CONSTRAINT fk_audit_logs_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE health_alerts (
	id INTEGER NOT NULL, 
	astronaut_id INTEGER NOT NULL, 
	measurement_id INTEGER, 
	level VARCHAR(10) NOT NULL, 
	metric VARCHAR(30) NOT NULL, 
	rule VARCHAR(20) NOT NULL, 
	title VARCHAR(160) NOT NULL, 
	what_changed TEXT NOT NULL, 
	why TEXT NOT NULL, 
	action TEXT NOT NULL, 
	contact TEXT NOT NULL, 
	source_ref TEXT, 
	status VARCHAR(15) NOT NULL, 
	review_notes TEXT, 
	reviewed_by_id INTEGER, 
	reviewed_at DATETIME, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	CONSTRAINT pk_health_alerts PRIMARY KEY (id), 
	CONSTRAINT ck_health_alerts_level_valid CHECK (level IN ('info','followup','priority')), 
	CONSTRAINT ck_health_alerts_status_valid CHECK (status IN ('open','acknowledged','resolved')), 
	CONSTRAINT fk_health_alerts_astronaut_id_astronauts FOREIGN KEY(astronaut_id) REFERENCES astronauts (id) ON DELETE CASCADE, 
	CONSTRAINT fk_health_alerts_measurement_id_health_measurements FOREIGN KEY(measurement_id) REFERENCES health_measurements (id) ON DELETE SET NULL, 
	CONSTRAINT fk_health_alerts_reviewed_by_id_users FOREIGN KEY(reviewed_by_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE health_measurements (
	id INTEGER NOT NULL, 
	astronaut_id INTEGER NOT NULL, 
	measured_at DATETIME NOT NULL, 
	heart_rate INTEGER, 
	systolic_bp INTEGER, 
	diastolic_bp INTEGER, 
	spo2 FLOAT, 
	temperature FLOAT, 
	respiratory_rate INTEGER, 
	sleep_hours FLOAT, 
	exercise_min INTEGER, 
	fatigue INTEGER, 
	mood INTEGER, 
	glucose INTEGER, 
	notes TEXT, 
	source VARCHAR(40) NOT NULL, 
	is_synthetic BOOLEAN NOT NULL, 
	recorded_by_id INTEGER, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	CONSTRAINT pk_health_measurements PRIMARY KEY (id), 
	CONSTRAINT ck_health_measurements_hr_range CHECK (heart_rate IS NULL OR heart_rate BETWEEN 25 AND 230), 
	CONSTRAINT ck_health_measurements_sbp_range CHECK (systolic_bp IS NULL OR systolic_bp BETWEEN 60 AND 260), 
	CONSTRAINT ck_health_measurements_dbp_range CHECK (diastolic_bp IS NULL OR diastolic_bp BETWEEN 30 AND 160), 
	CONSTRAINT ck_health_measurements_spo2_range CHECK (spo2 IS NULL OR spo2 BETWEEN 50 AND 100), 
	CONSTRAINT ck_health_measurements_temp_range CHECK (temperature IS NULL OR temperature BETWEEN 32 AND 43), 
	CONSTRAINT ck_health_measurements_rr_range CHECK (respiratory_rate IS NULL OR respiratory_rate BETWEEN 4 AND 60), 
	CONSTRAINT ck_health_measurements_sleep_range CHECK (sleep_hours IS NULL OR sleep_hours BETWEEN 0 AND 16), 
	CONSTRAINT ck_health_measurements_exercise_range CHECK (exercise_min IS NULL OR exercise_min BETWEEN 0 AND 400), 
	CONSTRAINT ck_health_measurements_fatigue_range CHECK (fatigue IS NULL OR fatigue BETWEEN 1 AND 7), 
	CONSTRAINT ck_health_measurements_mood_range CHECK (mood IS NULL OR mood BETWEEN 1 AND 5), 
	CONSTRAINT ck_health_measurements_glucose_range CHECK (glucose IS NULL OR glucose BETWEEN 20 AND 600), 
	CONSTRAINT fk_health_measurements_astronaut_id_astronauts FOREIGN KEY(astronaut_id) REFERENCES astronauts (id) ON DELETE CASCADE, 
	CONSTRAINT fk_health_measurements_recorded_by_id_users FOREIGN KEY(recorded_by_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE missions (
	id INTEGER NOT NULL, 
	code VARCHAR(30) NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	environment VARCHAR(40) NOT NULL, 
	start_date DATE NOT NULL, 
	duration_days INTEGER NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	description TEXT, 
	is_synthetic BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	CONSTRAINT pk_missions PRIMARY KEY (id), 
	CONSTRAINT ck_missions_duration_range CHECK (duration_days BETWEEN 1 AND 1500), 
	CONSTRAINT ck_missions_status_valid CHECK (status IN ('planned','active','completed')), 
	CONSTRAINT uq_missions_code UNIQUE (code)
);

CREATE TABLE users (
	id INTEGER NOT NULL, 
	full_name VARCHAR(120) NOT NULL, 
	email VARCHAR(160) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	role VARCHAR(20) NOT NULL, 
	is_active_account BOOLEAN NOT NULL, 
	last_login_at DATETIME, 
	is_demo BOOLEAN DEFAULT 0 NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	CONSTRAINT pk_users PRIMARY KEY (id), 
	CONSTRAINT ck_users_role_valid CHECK (role IN ('admin','doctor','operator'))
);

CREATE INDEX ix_alerts_status_level ON health_alerts (status, level);

CREATE INDEX ix_api_tokens_user_id ON api_tokens (user_id);

CREATE UNIQUE INDEX ix_astronauts_code ON astronauts (code);

CREATE INDEX ix_astronauts_mission_id ON astronauts (mission_id);

CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at);

CREATE INDEX ix_health_alerts_measurement_id ON health_alerts (measurement_id);

CREATE INDEX ix_measurements_astronaut_time ON health_measurements (astronaut_id, measured_at);

CREATE UNIQUE INDEX ix_users_email ON users (email);