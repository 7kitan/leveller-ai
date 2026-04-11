import logging
import os
import json
import sys

# Thiet lap encoding cho output
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Khoi tao logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger("diagnose_api")

# Cau hinh moi truong
os.environ['NEO4J_URI'] = 'bolt://localhost:7687'
os.environ['PYTHONPATH'] = 'backend'

try:
    from shared.taxonomy_service import taxonomy_service
    
    print("\n" + "="*50)
    print("PHAN TICH CHE DO: CHI XEM VI TRI (type='Position')")
    print("="*50)
    
    res = taxonomy_service.get_relationships_grouped(limit=100, parent_type='Position')
    
    print(f"\nKET QUA API: Tra ve {len(res)} nut cha.")
    for i, r in enumerate(res):
        print(f"  [{i+1}] {r['parent']} (Type: {r['parent_type']}, Children: {len(r['children'])})")
        if i < 2:
            print(f"      Sample: {[c['name'] for c in r['children'][:3]]}")

    print("\n" + "="*50)
    print("PHAN TICH CHE DO: TAT CA (type=None)")
    print("="*50)
    
    res_all = taxonomy_service.get_relationships_grouped(limit=100)
    positions_in_all = [r for r in res_all if r['parent_type'] == 'Position']
    
    print(f"\nKET QUA API: Tra ve {len(res_all)} nut cha tong cong.")
    print(f"Trong do co {len(positions_in_all)} nut la Vi tri (Position).")
    print(f"DANH SACH VI TRI TIM THAY: {[p['parent'] for p in positions_in_all]}")
    
    if len(positions_in_all) < 12:
        print("\n[!] CANH BAO: So luong vi tri trong che do 'All' dang it hon thuc te.")

except Exception as e:
    logger.error(f"Loi khi thuc thi chan doan: {e}", exc_info=True)
