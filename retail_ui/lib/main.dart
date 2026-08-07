import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

void main() => runApp(const MyApp());

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Retail Inventory System',
      theme: ThemeData(primarySwatch: Colors.blue),
      home: const InventoryScreen(),
    );
  }
}

// ============================================================
// PRODUCT MODEL
// ============================================================
class Product {
  final String id;
  final String barcode;
  final String sku;
  final String name;
  final String category;
  final double unitPrice;
  final double costPrice;
  final int quantityOnHand;
  final String storeId;

  Product({
    required this.id,
    required this.barcode,
    required this.sku,
    required this.name,
    required this.category,
    required this.unitPrice,
    required this.costPrice,
    required this.quantityOnHand,
    required this.storeId,
  });

  factory Product.fromJson(Map<String, dynamic> json) => Product(
        id: json['id'],
        barcode: json['barcode'],
        sku: json['sku'],
        name: json['name'],
        category: json['category'],
        unitPrice: (json['unit_price'] as num).toDouble(),
        costPrice: (json['cost_price'] as num).toDouble(),
        quantityOnHand: json['quantity_on_hand'],
        storeId: json['store_id'],
      );
}

// ============================================================
// API SERVICE
// ============================================================
class ApiService {
  static const String baseUrl = 'http://localhost:8002';

  static Future<List<Product>> fetchProducts(String storeId) async {
    final response = await http.get(
      Uri.parse('$baseUrl/products/?store_id=$storeId'),
    );
    if (response.statusCode == 200) {
      List<dynamic> data = json.decode(response.body);
      return data.map((json) => Product.fromJson(json)).toList();
    } else {
      throw Exception('Failed to load products: ${response.statusCode}');
    }
  }

  static Future<Product> createProduct(Map<String, dynamic> productData) async {
    final response = await http.post(
      Uri.parse('$baseUrl/products/'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode(productData),
    );
    if (response.statusCode == 201) {
      return Product.fromJson(json.decode(response.body));
    } else {
      throw Exception('Failed to create product');
    }
  }

  static Future<Product> updatePrice(String productId, double newPrice, String storeId) async {
    final response = await http.put(
      Uri.parse('$baseUrl/products/$productId'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({
        'unit_price': newPrice,
        'store_id': storeId,
      }),
    );
    if (response.statusCode == 200) {
      return Product.fromJson(json.decode(response.body));
    } else {
      throw Exception('Failed to update price');
    }
  }
}

// ============================================================
// MAIN SCREEN
// ============================================================
class InventoryScreen extends StatefulWidget {
  const InventoryScreen({super.key});

  @override
  State<InventoryScreen> createState() => _InventoryScreenState();
}

class _InventoryScreenState extends State<InventoryScreen> {
  final TextEditingController _storeController = TextEditingController(text: 'store-123-abc');
  List<Product> _products = [];
  bool _loading = false;
  String _error = '';

  // Form controllers
  final TextEditingController _barcodeController = TextEditingController();
  final TextEditingController _skuController = TextEditingController();
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _categoryController = TextEditingController();
  final TextEditingController _priceController = TextEditingController();
  final TextEditingController _costController = TextEditingController();
  final TextEditingController _qtyController = TextEditingController();

  Future<void> _loadProducts() async {
    setState(() {
      _loading = true;
      _error = '';
    });
    try {
      final products = await ApiService.fetchProducts(_storeController.text);
      setState(() => _products = products);
    } catch (e) {
      setState(() => _error = 'Failed to load: $e');
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _addProduct() async {
    try {
      final productData = {
        'barcode': _barcodeController.text,
        'sku': _skuController.text,
        'name': _nameController.text,
        'category': _categoryController.text,
        'unit_price': double.parse(_priceController.text),
        'cost_price': double.parse(_costController.text),
        'quantity_on_hand': int.parse(_qtyController.text),
        'store_id': _storeController.text,
      };
      await ApiService.createProduct(productData);
      _barcodeController.clear();
      _skuController.clear();
      _nameController.clear();
      _categoryController.clear();
      _priceController.clear();
      _costController.clear();
      _qtyController.clear();
      await _loadProducts();

      // FIX: Check if mounted before showing SnackBar
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('✅ Product added successfully!')),
        );
      }
    } catch (e) {
      // FIX: Check if mounted before showing SnackBar
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('❌ Error: $e'), backgroundColor: Colors.red),
        );
      }
    }
  }

  Future<void> _showPriceDialog(Product product) async {
    final TextEditingController priceController =
        TextEditingController(text: product.unitPrice.toString());
    final result = await showDialog<double>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Update Price for ${product.name}'),
        content: TextField(
          controller: priceController,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(labelText: 'New Price'),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
          TextButton(
            onPressed: () => Navigator.pop(context, double.parse(priceController.text)),
            child: const Text('Save'),
          ),
        ],
      ),
    );
    if (result != null) {
      try {
        await ApiService.updatePrice(product.id, result, _storeController.text);
        await _loadProducts();

        // FIX: Check if mounted before showing SnackBar
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('✅ Price updated! Check ESL Consumer terminal.')),
          );
        }
      } catch (e) {
        // FIX: Check if mounted before showing SnackBar
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('❌ Error: $e'), backgroundColor: Colors.red),
          );
        }
      }
    }
  }

  @override
  void initState() {
    super.initState();
    _loadProducts();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('📦 Retail Inventory System'),
        actions: [
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: ElevatedButton(
              onPressed: () {
                // Future: Switch between Web/Desktop themes
              },
              style: ElevatedButton.styleFrom(backgroundColor: Colors.green),
              child: const Text('⚡ Event Bus: Active'),
            ),
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Left: Add Product Form (30%)
            Expanded(
              flex: 3,
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      const Text(
                        '➕ Add New Product',
                        style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 16),
                      TextField(
                        controller: _barcodeController,
                        decoration: const InputDecoration(labelText: 'Barcode', border: OutlineInputBorder()),
                      ),
                      const SizedBox(height: 8),
                      TextField(
                        controller: _skuController,
                        decoration: const InputDecoration(labelText: 'SKU', border: OutlineInputBorder()),
                      ),
                      const SizedBox(height: 8),
                      TextField(
                        controller: _nameController,
                        decoration: const InputDecoration(labelText: 'Name', border: OutlineInputBorder()),
                      ),
                      const SizedBox(height: 8),
                      TextField(
                        controller: _categoryController,
                        decoration: const InputDecoration(labelText: 'Category', border: OutlineInputBorder()),
                      ),
                      const SizedBox(height: 8),
                      TextField(
                        controller: _priceController,
                        decoration: const InputDecoration(labelText: 'Unit Price', border: OutlineInputBorder()),
                        keyboardType: TextInputType.number,
                      ),
                      const SizedBox(height: 8),
                      TextField(
                        controller: _costController,
                        decoration: const InputDecoration(labelText: 'Cost Price', border: OutlineInputBorder()),
                        keyboardType: TextInputType.number,
                      ),
                      const SizedBox(height: 8),
                      TextField(
                        controller: _qtyController,
                        decoration: const InputDecoration(labelText: 'Quantity on Hand', border: OutlineInputBorder()),
                        keyboardType: TextInputType.number,
                      ),
                      const SizedBox(height: 16),
                      ElevatedButton(
                        onPressed: _addProduct,
                        child: const Text('Add Product'),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(width: 16),
            // Right: Product List (70%)
            Expanded(
              flex: 7,
              child: Column(
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _storeController,
                          decoration: const InputDecoration(
                            labelText: 'Store ID',
                            border: OutlineInputBorder(),
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      ElevatedButton(
                        onPressed: _loadProducts,
                        child: const Text('🔍 Load Products'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  if (_loading) const CircularProgressIndicator(),
                  if (_error.isNotEmpty) Text(_error, style: const TextStyle(color: Colors.red)),
                  if (!_loading && _products.isNotEmpty)
                    Expanded(
                      child: ListView.builder(
                        itemCount: _products.length,
                        itemBuilder: (context, index) {
                          final p = _products[index];
                          return Card(
                            child: ListTile(
                              title: Text(p.name),
                              subtitle: Text(
                                'Barcode: ${p.barcode} | SKU: ${p.sku} | Qty: ${p.quantityOnHand}',
                              ),
                              trailing: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Text('KES ${p.unitPrice}'),
                                  const SizedBox(width: 8),
                                  IconButton(
                                    icon: const Icon(Icons.edit, color: Colors.blue),
                                    onPressed: () => _showPriceDialog(p),
                                  ),
                                ],
                              ),
                            ),
                          );
                        },
                      ),
                    ),
                  if (!_loading && _products.isEmpty)
                    const Text('No products found for this store.'),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}