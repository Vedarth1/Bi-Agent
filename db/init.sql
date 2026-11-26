
-- ==========================================
-- Database Initialization Script
-- File: db/init.sql
-- Database: PostgreSQL
-- ==========================================

-- Drop existing tables (child tables first)
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

-- ==========================================
-- 1. CUSTOMERS
-- ==========================================

CREATE TABLE customers (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    country VARCHAR(50) NOT NULL
        CHECK (country IN (
            'India',
            'USA',
            'UK',
            'Germany',
            'Canada',
            'Australia'
        )),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- 2. PRODUCTS
-- ==========================================

CREATE TABLE products (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    category VARCHAR(50) NOT NULL
        CHECK (category IN (
            'electronics',
            'apparel',
            'home',
            'beauty',
            'sports'
        )),
    price NUMERIC(12, 2) NOT NULL CHECK (price >= 0)
);

-- ==========================================
-- 3. ORDERS
-- ==========================================

CREATE TABLE orders (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    order_date TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    total_amount NUMERIC(12, 2) NOT NULL CHECK (total_amount >= 0),

    CONSTRAINT fk_orders_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(id)
        ON DELETE RESTRICT
);

-- ==========================================
-- 4. ORDER ITEMS
-- ==========================================

CREATE TABLE order_items (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(12, 2) NOT NULL CHECK (unit_price >= 0),

    CONSTRAINT fk_order_items_order
        FOREIGN KEY (order_id)
        REFERENCES orders(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_order_items_product
        FOREIGN KEY (product_id)
        REFERENCES products(id)
        ON DELETE RESTRICT
);

-- ==========================================
-- INDEXES FOR QUERY PERFORMANCE
-- ==========================================

CREATE INDEX idx_orders_customer_id
    ON orders(customer_id);

CREATE INDEX idx_orders_order_date
    ON orders(order_date);

CREATE INDEX idx_order_items_order_id
    ON order_items(order_id);

CREATE INDEX idx_order_items_product_id
    ON order_items(product_id);

CREATE INDEX idx_customers_country
    ON customers(country);

CREATE INDEX idx_products_category
    ON products(category);

-- ==========================================
-- 5. SEED DATA
-- ==========================================

INSERT INTO customers (name, country) VALUES
    ('Aarav Sharma', 'India'),
    ('Priya Patel', 'India'),
    ('John Smith', 'USA'),
    ('Emily Johnson', 'USA'),
    ('Oliver Brown', 'UK'),
    ('Sophie Wilson', 'UK'),
    ('Lukas Muller', 'Germany'),
    ('Anna Schmidt', 'Germany'),
    ('Liam Tremblay', 'Canada'),
    ('Chloe Martin', 'Australia');

INSERT INTO products (name, category, price) VALUES
    ('Laptop Pro 14', 'electronics', 1299.00),
    ('Wireless Earbuds', 'electronics', 89.99),
    ('Smart Watch', 'electronics', 249.50),
    ('Cotton T-Shirt', 'apparel', 19.99),
    ('Denim Jacket', 'apparel', 79.00),
    ('Running Shoes', 'sports', 119.00),
    ('Yoga Mat', 'sports', 35.00),
    ('Coffee Maker', 'home', 99.00),
    ('Desk Lamp', 'home', 45.00),
    ('Perfume Set', 'beauty', 65.00);

-- 300 orders spread over the last year
INSERT INTO orders (customer_id, order_date, total_amount)
SELECT
    1 + FLOOR(random() * 10)::int,
    now() - (random() * 365)::int * interval '1 day',
    0                                  
FROM generate_series(1, 300);

-- 1-3 items per order
INSERT INTO order_items (order_id, product_id, quantity, unit_price)
SELECT
    o.id,
    p.id,
    p.price,
    1 + FLOOR(random() * 3)::int
FROM orders o
CROSS JOIN LATERAL (
    SELECT id, price FROM products ORDER BY random() LIMIT 1
) p
CROSS JOIN LATERAL generate_series(1, 1 + FLOOR(random() * 3)::int) AS n;

-- roll item sums back up into orders.total_amount
UPDATE orders o
SET total_amount = agg.total
FROM (
    SELECT order_id, SUM(quantity * unit_price) AS total
    FROM order_items
    GROUP BY order_id
) agg
WHERE agg.order_id = o.id;