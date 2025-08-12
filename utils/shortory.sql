-- ==========================================
-- DB 생성/선택
-- ==========================================
CREATE DATABASE IF NOT EXISTS shortory
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;
USE shortory;

-- ==========================================
-- users
-- ==========================================
CREATE TABLE IF NOT EXISTS users (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  name       VARCHAR(50)  NOT NULL,
  email      VARCHAR(100) NOT NULL,
  phone      VARCHAR(20)  NOT NULL,
  user_id    VARCHAR(50)  NOT NULL,
  password   VARCHAR(100) NOT NULL,
  role       ENUM('creator','reviewer') NOT NULL DEFAULT 'creator',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_users_user_id (user_id),
  UNIQUE KEY uq_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ==========================================
-- posts
-- ==========================================
CREATE TABLE IF NOT EXISTS posts (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  creator_id    INT NOT NULL,
  title         VARCHAR(255) NOT NULL,
  description   TEXT NOT NULL,
  is_deleted    TINYINT(1) NOT NULL DEFAULT 0,
  is_recruiting TINYINT(1) DEFAULT 1,
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  video_link    TEXT,
  CONSTRAINT fk_posts_users
    FOREIGN KEY (creator_id) REFERENCES users(id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  KEY ix_posts_creator (creator_id),
  KEY ix_posts_list   (is_recruiting, is_deleted, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ==========================================
-- reviewer_post
-- ==========================================
CREATE TABLE IF NOT EXISTS reviewer_post (
  id               INT AUTO_INCREMENT PRIMARY KEY,
  reviewer_id      INT NOT NULL,
  post_id          INT NOT NULL,
  created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
  status           VARCHAR(20) DEFAULT '대기 중',
  task_id          VARCHAR(100),
  review_completed TINYINT(1) DEFAULT 0,
  CONSTRAINT fk_rp_reviewer
    FOREIGN KEY (reviewer_id) REFERENCES users(id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_rp_post
    FOREIGN KEY (post_id) REFERENCES posts(id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  UNIQUE KEY uq_rp_reviewer_post (reviewer_id, post_id),
  KEY ix_rp_post (post_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ==========================================
-- shorts_result
-- ==========================================
CREATE TABLE IF NOT EXISTS shorts_result (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  post_id     INT NOT NULL,
  reviewer_id INT NOT NULL,
  filename    VARCHAR(255) NOT NULL,
  emotion     VARCHAR(50),
  timestamp   VARCHAR(50),
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_sr_post
    FOREIGN KEY (post_id) REFERENCES posts(id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_sr_reviewer
    FOREIGN KEY (reviewer_id) REFERENCES users(id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  KEY ix_sr_owner (post_id, reviewer_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ==========================================
-- reviewer_results
-- ==========================================
CREATE TABLE IF NOT EXISTS reviewer_results (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  reviewer_id  INT NOT NULL,
  post_id      INT NOT NULL,
  filename     VARCHAR(255),
  emotion      VARCHAR(50),
  timestamp    VARCHAR(50),
  created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  selected     TINYINT(1) NOT NULL DEFAULT 0,
  submitted    TINYINT(1) NOT NULL DEFAULT 0,
  submitted_at DATETIME NULL,
  CONSTRAINT fk_rr_reviewer
    FOREIGN KEY (reviewer_id) REFERENCES users(id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_rr_post
    FOREIGN KEY (post_id) REFERENCES posts(id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  KEY ix_rr_owner        (post_id, reviewer_id),
  KEY ix_rr_submit_state (post_id, reviewer_id, submitted, selected),
  KEY ix_rr_created      (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ==========================================
-- short_clips
-- ==========================================
CREATE TABLE IF NOT EXISTS short_clips (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  reviewer_id   INT NOT NULL,
  post_id       INT NOT NULL,
  clip_filename VARCHAR(255) NOT NULL,
  submitted_at  DATETIME NOT NULL,
  CONSTRAINT fk_sc_reviewer
    FOREIGN KEY (reviewer_id) REFERENCES users(id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_sc_post
    FOREIGN KEY (post_id) REFERENCES posts(id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  KEY ix_sc_owner (post_id, reviewer_id, submitted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ==========================================
-- saved_clips
-- ==========================================
CREATE TABLE IF NOT EXISTS saved_clips (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  reviewer_id INT NOT NULL,
  post_id     INT NOT NULL,
  filename    VARCHAR(255) NOT NULL,
  emotion     VARCHAR(50),
  timestamp   VARCHAR(50),
  saved_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_saved (reviewer_id, post_id, filename),
  CONSTRAINT fk_saved_reviewer
    FOREIGN KEY (reviewer_id) REFERENCES users(id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_saved_post
    FOREIGN KEY (post_id) REFERENCES posts(id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =================================================================
-- 별점/코인
-- =================================================================
CREATE TABLE IF NOT EXISTS reviewer_ratings (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  post_id     INT NOT NULL,
  reviewer_id INT NOT NULL,
  creator_id  INT NOT NULL,
  rating      TINYINT NOT NULL,
  comment     TEXT NULL,
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at  TIMESTAMP NULL DEFAULT NULL,
  CONSTRAINT fk_rate_post
    FOREIGN KEY (post_id) REFERENCES posts(id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_rate_reviewer
    FOREIGN KEY (reviewer_id) REFERENCES users(id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_rate_creator
    FOREIGN KEY (creator_id) REFERENCES users(id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  UNIQUE KEY uq_rating_once (post_id, reviewer_id, creator_id),
  KEY ix_rating_reviewer (reviewer_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS reviewer_points (
  user_id    INT PRIMARY KEY,
  balance    INT UNSIGNED NOT NULL DEFAULT 0,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                     ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_wallet_user
    FOREIGN KEY (user_id) REFERENCES users(id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS point_transactions (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  user_id    INT NOT NULL,
  delta      INT NOT NULL,
  reason     VARCHAR(32) NOT NULL DEFAULT 'rating_reward',
  post_id    INT NULL,
  rating_id  INT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_pt_user
    FOREIGN KEY (user_id) REFERENCES users(id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_pt_post
    FOREIGN KEY (post_id) REFERENCES posts(id)
    ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT fk_pt_rating
    FOREIGN KEY (rating_id) REFERENCES reviewer_ratings(id)
    ON DELETE SET NULL ON UPDATE CASCADE,
  KEY ix_pt_user_time (user_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE OR REPLACE VIEW reviewer_rating_summary AS
SELECT
  r.reviewer_id,
  AVG(r.rating) AS avg_rating,
  COUNT(*)      AS rating_count,
  MAX(r.updated_at) AS last_update
FROM reviewer_ratings r
GROUP BY r.reviewer_id;

-- ==========================================
-- 상점(카테고리/브랜드/상품)
-- ==========================================
CREATE TABLE IF NOT EXISTS shop_categories (
  id INT AUTO_INCREMENT PRIMARY KEY,
  category_key VARCHAR(32) UNIQUE NOT NULL,  -- giftcard / avatar / digital / food / beauty
  label        VARCHAR(50) NOT NULL,
  sort_order   INT DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS shop_subcategories (
  id INT AUTO_INCREMENT PRIMARY KEY,
  category_id INT NOT NULL,
  label       VARCHAR(50) NOT NULL,
  sort_order  INT DEFAULT 0,
  UNIQUE KEY uq_cat_label (category_id, label),
  CONSTRAINT fk_sub_cat FOREIGN KEY (category_id) REFERENCES shop_categories(id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS shop_brands (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name      VARCHAR(80) UNIQUE NOT NULL,
  logo_path VARCHAR(255) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS shop_products (
  id             INT AUTO_INCREMENT PRIMARY KEY,
  brand_id       INT NULL,
  category_key   VARCHAR(32) NOT NULL,     -- 문자열 키로 통일 (CSV와 동일)
  subcategory_id INT NULL,
  name           VARCHAR(120) NOT NULL,
  short_desc     VARCHAR(200) NULL,
  badge          VARCHAR(40) NULL,
  star_price     INT UNSIGNED NOT NULL,
  cash_price     INT UNSIGNED NULL,
  image_path     VARCHAR(255) NOT NULL,
  is_active      TINYINT(1) DEFAULT 1,
  created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_prod_brand  FOREIGN KEY (brand_id)     REFERENCES shop_brands(id)
    ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT fk_prod_catkey FOREIGN KEY (category_key)  REFERENCES shop_categories(category_key)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_prod_sub    FOREIGN KEY (subcategory_id) REFERENCES shop_subcategories(id)
    ON DELETE SET NULL ON UPDATE CASCADE,
  INDEX ix_prod_active (is_active),
  INDEX ix_prod_catkey (category_key),
  INDEX ix_prod_sub (subcategory_id),
  INDEX ix_prod_brand (brand_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ==========================================
-- CSV 컬럼과 동일한 이름으로 조회 제공하는 뷰
-- (프론트/템플릿/리포트에서 이 뷰만 SELECT 하면 컬럼명이 항상 CSV와 동일)
-- ==========================================
CREATE OR REPLACE VIEW v_shop_products AS
SELECT
  p.id,
  b.name             AS brand_name,
  c.category_key,
  sc.label           AS subcategory_label,
  p.name,
  p.short_desc,
  p.badge,
  p.star_price,
  p.cash_price,
  p.image_path,
  p.is_active,
  p.created_at
FROM shop_products p
JOIN shop_categories      c  ON c.category_key = p.category_key
LEFT JOIN shop_subcategories sc ON sc.id = p.subcategory_id
LEFT JOIN shop_brands      b  ON b.id = p.brand_id;

-- ==========================================
-- 초기 카테고리 (VALUES(deprecated) 회피: 행 별칭 사용)
-- ==========================================
INSERT INTO shop_categories (category_key, label, sort_order)
VALUES
 ('giftcard','교환권',10),
 ('avatar','패션',20),
 ('digital','디지털',30),
 ('food','식품',40),
 ('beauty','뷰티',50)
AS v(category_key, label, sort_order)
ON DUPLICATE KEY UPDATE
  label = v.label,
  sort_order = v.sort_order;

-- 확인
SHOW TABLES;
