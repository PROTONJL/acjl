-- ============================================================
-- 个人记账本 - 初始数据
-- 执行方式：
--   mysql -u root -p --default-character-set=utf8mb4 < sql/02_seed.sql
-- 说明：脚本可重复执行（使用 INSERT IGNORE / 先查后插）
-- ============================================================

SET NAMES utf8mb4;
USE `ledger`;

-- ------------------------------------------------------------
-- 1. 系统预置分类（user_id = NULL）
-- ------------------------------------------------------------
INSERT IGNORE INTO `categories` (`user_id`, `name`, `type`, `icon`, `sort_order`) VALUES
  (NULL, '餐饮',     'expense', '🍜', 10),
  (NULL, '交通',     'expense', '🚌', 20),
  (NULL, '购物',     'expense', '🛍️', 30),
  (NULL, '居住',     'expense', '🏠', 40),
  (NULL, '娱乐',     'expense', '🎮', 50),
  (NULL, '医疗',     'expense', '💊', 60),
  (NULL, '教育',     'expense', '📚', 70),
  (NULL, '通讯',     'expense', '📱', 80),
  (NULL, '其他支出', 'expense', '📦', 90),
  (NULL, '工资',     'income',  '💰', 10),
  (NULL, '奖金',     'income',  '🏆', 20),
  (NULL, '兼职',     'income',  '🧰', 30),
  (NULL, '投资收益', 'income',  '📈', 40),
  (NULL, '红包',     'income',  '🧧', 50),
  (NULL, '其他收入', 'income',  '✨', 60);

-- ------------------------------------------------------------
-- 2. 演示账号（可选）
--    用户名：demo   密码：Demo1234
--    password_hash 由 bcrypt(cost=12) 生成，可直接用于登录验证
-- ------------------------------------------------------------
INSERT INTO `users` (`username`, `email`, `password_hash`, `nickname`, `is_active`)
SELECT 'demo', 'demo@example.com',
       '$2b$12$zDvkiJ6ntc1jGLPSnJDHPeQ4hCUJbT9Lt/4Wk6x2q7aVK9ZXTZ2U2',
       '演示账号', 1
WHERE NOT EXISTS (SELECT 1 FROM `users` WHERE `username` = 'demo');
