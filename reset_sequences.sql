-- Script para resetear todas las secuencias de autoincremento en PostgreSQL
-- Ejecutar esto cuando los IDs autoincrementables fallen con errores de "duplicate key"

-- Resetear secuencia de product
SELECT setval(pg_get_serial_sequence('product', 'id'), 
       COALESCE((SELECT MAX(id) FROM product), 0) + 1, 
       false);

-- Resetear secuencia de product_variant
SELECT setval(pg_get_serial_sequence('product_variant', 'id'), 
       COALESCE((SELECT MAX(id) FROM product_variant), 0) + 1, 
       false);

-- Resetear secuencia de category
SELECT setval(pg_get_serial_sequence('category', 'id'), 
       COALESCE((SELECT MAX(id) FROM category), 0) + 1, 
       false);

-- Resetear secuencia de order (escapado porque es palabra reservada)
SELECT setval(pg_get_serial_sequence('order', 'id'), 
       COALESCE((SELECT MAX(id) FROM "order"), 0) + 1, 
       false);

-- Resetear secuencia de orderdetail
SELECT setval(pg_get_serial_sequence('orderdetail', 'id'), 
       COALESCE((SELECT MAX(id) FROM orderdetail), 0) + 1, 
       false);

-- Resetear secuencia de client_cart_item
SELECT setval(pg_get_serial_sequence('client_cart_item', 'id'), 
       COALESCE((SELECT MAX(id) FROM client_cart_item), 0) + 1, 
       false);

-- Resetear secuencia de cake_flavor
SELECT setval(pg_get_serial_sequence('cake_flavor', 'id'), 
       COALESCE((SELECT MAX(id) FROM cake_flavor), 0) + 1, 
       false);

-- Resetear secuencia de cake_filling
SELECT setval(pg_get_serial_sequence('cake_filling', 'id'), 
       COALESCE((SELECT MAX(id) FROM cake_filling), 0) + 1, 
       false);

-- Resetear secuencia de cake_topping
SELECT setval(pg_get_serial_sequence('cake_topping', 'id'), 
       COALESCE((SELECT MAX(id) FROM cake_topping), 0) + 1, 
       false);

-- Resetear secuencia de custom_cake_request
SELECT setval(pg_get_serial_sequence('custom_cake_request', 'id'), 
       COALESCE((SELECT MAX(id) FROM custom_cake_request), 0) + 1, 
       false);

-- Verificar las secuencias actuales
SELECT 
    'product' as tabla, 
    last_value as siguiente_id 
FROM product_id_seq
UNION ALL
SELECT 
    'product_variant' as tabla, 
    last_value as siguiente_id 
FROM product_variant_id_seq
UNION ALL
SELECT 
    'category' as tabla, 
    last_value as siguiente_id 
FROM category_id_seq;
