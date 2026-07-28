-- Insert sample products
INSERT INTO public.products (barcode, sku, name, category, unit_price, cost_price, quantity_on_hand, store_id)
VALUES 
    ('1234567890', 'TEST-001', 'Sample Product Alpha', 'test', 100.00, 50.00, 100, '00000000-0000-0000-0000-000000000001'),
    ('0987654321', 'TEST-002', 'Sample Product Beta', 'electronics', 500.00, 250.00, 50, '00000000-0000-0000-0000-000000000001'),
    ('1122334455', 'TEST-003', 'Sample Product Gamma', 'food', 75.50, 40.00, 200, '00000000-0000-0000-0000-000000000001')
ON CONFLICT (barcode) DO NOTHING;

-- Verify data was inserted
SELECT * FROM public.products;