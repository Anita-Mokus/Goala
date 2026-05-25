ALTER TABLE app_settings
ADD COLUMN dataset_name VARCHAR(50) NOT NULL
DEFAULT 'liverag';

ALTER TABLE chat_history
ADD COLUMN dataset_name VARCHAR(50) NOT NULL
DEFAULT 'liverag';

