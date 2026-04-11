import os
os.environ["NEO4J_URI"] = "bolt://localhost:7687"

from shared.taxonomy_service import taxonomy_service
import json

def debug_grouped_api():
    print("\n--- DEBUG: get_relationships_grouped(limit=50, parent_type='Position') ---")
    results = taxonomy_service.get_relationships_grouped(limit=50, parent_type='Position')
    
    print(f"Total results returned: {len(results)}")
    for i, res in enumerate(results):
        print(f"{i+1}. Parent: {res['parent']} (Type: {res['parent_type']}, Children: {len(res['children'])})")

    print("\n--- DEBUG: get_relationships_grouped(limit=50, parent_type=None) ---")
    results_all = taxonomy_service.get_relationships_grouped(limit=50)
    print(f"Total results (all) returned: {len(results_all)}")
    
    positions_in_all = [r for r in results_all if r['parent_type'] in ['Position', 'Role']]
    print(f"Positions found in 'all' results: {len(positions_in_all)}")
    for i, res in enumerate(positions_in_all):
         print(f"   - {res['parent']} (Type: {res['parent_type']})")

if __name__ == "__main__":
    debug_grouped_api()
