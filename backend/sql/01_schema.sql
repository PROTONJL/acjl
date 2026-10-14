-- ============================================================
-- 个人记账本 - 建库 / 建表脚本（MySQL 8.0，兼容 5.7）
-- 执行方式：
--   mysql -u root -p --default-character-set=utf8mb4 < sql/01_schema.sql
-- ============================================================

SET NAMES utf8mb4;

-- 需要从零重建时，手动放开下面两行（会删除所有数据！）
-- DROP DATABASE IF EXISTS `ledger`;
-- CREATE DATABASE `ledger` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS `ledger`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `ledger`;

-- ------------------------------------------------------------
-- 1. 用户表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `users` (
  `id`            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `username`      VARCHAR(50)  NOT NULL                     COMMENT '登录名，唯一',
  `email`         VARCHAR(100) DEFAULT NULL                 COMMENT '邮箱，可为空，唯一',
  `password_hash` VARCHAR(255) NOT NULL                     COMMENT 'bcrypt 加盐哈希，禁止存明文',
  `nickname`      VARCHAR(50)  DEFAULT NULL                 COMMENT '昵称',
  `is_active`     TINYINT(1)   NOT NULL DEFAULT 1           COMMENT '1=启用 0=停用',
  `created_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_users_username` (`username`),
  UNIQUE KEY `uk_users_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- ------------------------------------------------------------
-- 2. 收支分类表
--    user_id 为 NULL 表示系统预置分类（所有用户可见、不可删改）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `categories` (
  `id`         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id`    BIGINT UNSIGNED DEFAULT NULL               COMMENT 'NULL=系统预置分类',
  `name`       VARCHAR(30) NOT NULL,
  `type`       ENUM('income','expense') NOT NULL          COMMENT 'income=收入 expense=支出',
  `icon`       VARCHAR(50) DEFAULT NULL                   COMMENT '图标（emoji）',
  `sort_order` INT NOT NULL DEFAULT 0,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_categories_user_name_type` (`user_id`, `name`, `type`),
  KEY `idx_categories_type` (`type`),
  CONSTRAINT `fk_categories_user` FOREIGN KEY (`user_id`)
    REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='收支分类表';

-- ------------------------------------------------------------
-- 3. 收支明细表
--    amount 恒为正数，收支方向由 type 决定
--    软删除：is_deleted=1 表示已删除，查询一律带 is_deleted=0
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `transactions` (
  `id`          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id`     BIGINT UNSIGNED NOT NULL,
  `category_id` BIGINT UNSIGNED NOT NULL,
  `type`        ENUM('income','expense') NOT NULL,
  `amount`      DECIMAL(12,2) NOT NULL                            COMMENT '金额，必须 > 0',
  `remark`      VARCHAR(255) DEFAULT NULL                         COMMENT '备注',
  `occurred_at` DATE NOT NULL                                     COMMENT '记账日期',
  `is_deleted`  TINYINT(1) NOT NULL DEFAULT 0                     COMMENT '软删除标记',
  `created_at`  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_tx_user_occurred` (`user_id`, `occurred_at` DESC),
  KEY `idx_tx_user_type` (`user_id`, `type`),
  KEY `idx_tx_user_category` (`user_id`, `category_id`),
  CONSTRAINT `chk_tx_amount`    CHECK (`amount` > 0),
  CONSTRAINT `fk_tx_user`       FOREIGN KEY (`user_id`)
    REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_tx_category`   FOREIGN KEY (`category_id`)
    REFERENCES `categories` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='收支明细表';
