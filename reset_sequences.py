#!/usr/bin/env python3
"""
Script para resetear las secuencias de autoincremento en PostgreSQL.

Uso:
  python reset_sequences.py [--production]

Por defecto usa la base de datos local.
Con --production usa la base de datos de producción.
"""

import sys
from sqlalchemy import create_engine, text

# Configuración de bases de datos
LOCAL_DB = "postgresql://rouse:pass123@localhost:5440/main"
PROD_DB = "postgresql://postgres:ojdHdLuYrYxXfdCXQhySQBFYGSKMxJpo@metro.proxy.rlwy.net:49129/railway"

# Tablas que tienen ID autoincremental
TABLES = [
    'product',
    'product_variant',
    'category',
    '"order"',  # Escapado porque es palabra reservada SQL
    'order_detail',
    'client_cart_item',
    'cake_flavor',
    'cake_filling',
    'cake_topping',
    'custom_cake_request'
]


def reset_sequences(database_url: str):
    """Resetea las secuencias de autoincremento para todas las tablas."""
    engine = create_engine(database_url)
    
    print(f"\n🔧 Conectando a la base de datos...")
    print(f"   URL: {database_url.split('@')[1] if '@' in database_url else database_url}\n")
    
    with engine.connect() as conn:
        for table in TABLES:
            try:
                # Extraer el nombre sin comillas para pg_get_serial_sequence
                table_clean = table.strip('"')
                
                result = conn.execute(text(f"""
                    SELECT setval(
                        pg_get_serial_sequence('{table_clean}', 'id'), 
                        COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, 
                        false
                    )
                """))
                conn.commit()
                
                # Obtener el valor de la secuencia
                new_val = result.scalar()
                print(f'✓ {table_clean:25s} → siguiente ID: {new_val}')
                
            except Exception as e:
                conn.rollback()
                print(f'⚠ {table_clean:25s} → ERROR: {str(e)[:80]}')
    
    print('\n✅ Proceso completado\n')


def main():
    """Función principal."""
    use_production = '--production' in sys.argv or '-p' in sys.argv
    
    if use_production:
        print("\n" + "="*60)
        print("⚠️  ATENCIÓN: Vas a modificar la base de datos de PRODUCCIÓN")
        print("="*60)
        response = input("\n¿Estás seguro? Escribe 'SI' para continuar: ")
        if response != 'SI':
            print("\n❌ Operación cancelada\n")
            return
        
        db_url = PROD_DB
        print("\n🚀 Usando base de datos de PRODUCCIÓN")
    else:
        db_url = LOCAL_DB
        print("\n🏠 Usando base de datos LOCAL")
    
    reset_sequences(db_url)


if __name__ == "__main__":
    main()
