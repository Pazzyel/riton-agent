CREATE TABLE IF NOT EXISTS `knowledge_bases` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `file_hash` VARCHAR(64) NOT NULL,
  `name` VARCHAR(255) NOT NULL,
  `category` VARCHAR(100) NULL,
  `original_filename` VARCHAR(255) NOT NULL,
  `file_size` INT NOT NULL,
  `content_type` VARCHAR(100) NULL,
  `storage_key` VARCHAR(500) NULL,
  `storage_url` VARCHAR(1000) NULL,
  `uploaded_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `last_accessed_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `access_count` INT NOT NULL DEFAULT 1,
  `question_count` INT NOT NULL DEFAULT 0,
  `vector_status` ENUM('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED') NOT NULL DEFAULT 'PENDING',
  `vector_error` VARCHAR(500) NULL,
  `chunk_count` INT NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_knowledge_bases_file_hash` (`file_hash`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `rag_chat_sessions` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `title` VARCHAR(255) NOT NULL,
  `status` VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `message_count` INT NOT NULL DEFAULT 0,
  `is_pinned` BOOLEAN NOT NULL DEFAULT FALSE,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `rag_chat_messages` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `session_id` INT NOT NULL,
  `type` VARCHAR(20) NOT NULL,
  `content` TEXT NOT NULL,
  `message_order` INT NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `completed` BOOLEAN NOT NULL DEFAULT TRUE,
  PRIMARY KEY (`id`),
  KEY `ix_rag_chat_messages_session_id` (`session_id`),
  CONSTRAINT `fk_rag_chat_messages_session_id` FOREIGN KEY (`session_id`) REFERENCES `rag_chat_sessions` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `rag_session_knowledge_bases` (
  `session_id` INT NOT NULL,
  `knowledge_base_id` INT NOT NULL,
  PRIMARY KEY (`session_id`, `knowledge_base_id`),
  FOREIGN KEY (`session_id`) REFERENCES `rag_chat_sessions` (`id`) ON DELETE CASCADE,
  FOREIGN KEY (`knowledge_base_id`) REFERENCES `knowledge_bases` (`id`) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS `chat_sessions` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `title` VARCHAR(255) NOT NULL,
  `status` VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `message_count` INT NOT NULL DEFAULT 0,
  `is_pinned` BOOLEAN NOT NULL DEFAULT FALSE,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `chat_messages` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `session_id` INT NOT NULL,
  `type` VARCHAR(20) NOT NULL,
  `content` TEXT NOT NULL,
  `message_order` INT NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `completed` BOOLEAN NOT NULL DEFAULT TRUE,
  PRIMARY KEY (`id`),
  KEY `ix_chat_messages_session_id` (`session_id`),
  CONSTRAINT `fk_chat_messages_session_id` FOREIGN KEY (`session_id`) REFERENCES `chat_sessions` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


