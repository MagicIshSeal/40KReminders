import requests
import os
import json
from pathlib import Path
from catConvert import convert_to_json

GITHUB_REPO = "BSData/wh40k-10e"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents"
CACHE_DIR = Path("catalog_cache")
GAME_SYSTEM_FILE = "Warhammer 40,000.gst"

class CatalogDownloader:
    def __init__(self):
        self.cache_dir = CACHE_DIR
        self.cache_dir.mkdir(exist_ok=True)
        self.available_catalogs = None
    
    def download_game_system(self):
        """Download the game system file if not cached"""
        gst_file = self.cache_dir / GAME_SYSTEM_FILE
        json_file = self.cache_dir / GAME_SYSTEM_FILE.replace('.gst', '.json')
        
        if json_file.exists():
            return str(json_file)
        
        try:
            response = requests.get(GITHUB_API_URL, timeout=10)
            response.raise_for_status()
            files = response.json()
            
            gst_info = next((f for f in files if f['name'] == GAME_SYSTEM_FILE), None)
            if not gst_info:
                return None
            
            print(f"Downloading game system file...")
            response = requests.get(gst_info['download_url'], timeout=30)
            response.raise_for_status()
            
            with open(gst_file, 'wb') as f:
                f.write(response.content)
            
            print("Converting game system to JSON...")
            convert_to_json(str(gst_file), str(json_file))
            
            return str(json_file)
        except Exception as e:
            print(f"Error downloading game system: {e}")
            return None
    
    def fetch_available_catalogs(self):
        """Fetch list of available .cat files from GitHub repo"""
        try:
            response = requests.get(GITHUB_API_URL, timeout=10)
            response.raise_for_status()
            
            files = response.json()
            catalogs = []
            
            for file in files:
                if file['name'].endswith('.cat'):
                    catalogs.append({
                        'name': file['name'],
                        'display_name': file['name'].replace('.cat', ''),
                        'download_url': file['download_url'],
                        'size': file['size']
                    })
            
            self.available_catalogs = sorted(catalogs, key=lambda x: x['display_name'])
            return self.available_catalogs
        
        except requests.RequestException as e:
            print(f"Error fetching catalog list: {e}")
            return None
    
    def download_catalog(self, catalog_name):
        """Download a specific catalog file"""
        if not self.available_catalogs:
            self.fetch_available_catalogs()
        
        # Normalize catalog name for matching
        # Remove "Adeptus Astartes" as it's redundant with "Space Marines"
        normalized_name = catalog_name.replace('Adeptus Astartes - ', '').replace('Astartes - ', '')
        
        # Find the catalog
        catalog = None
        for cat in self.available_catalogs:
            # Try exact match first
            if normalized_name.lower() == cat['display_name'].lower():
                catalog = cat
                break
            # Try substring match
            elif normalized_name.lower() in cat['display_name'].lower():
                catalog = cat
                break
            # Try reverse substring match (catalog name in search string)
            elif cat['display_name'].lower() in normalized_name.lower():
                catalog = cat
                break
        
        if not catalog:
            print(f"Catalog '{catalog_name}' not found.")
            print(f"Tried normalizing to: '{normalized_name}'")
            return None
        
        # Check if already cached
        cat_file = self.cache_dir / catalog['name']
        json_file = self.cache_dir / catalog['name'].replace('.cat', '.json')
        
        if json_file.exists():
            print(f"✓ Using cached catalog: {catalog['display_name']}")
            return str(json_file)
        
        # Download the .cat file
        print(f"Downloading {catalog['display_name']}... ({catalog['size'] // 1024} KB)")
        try:
            response = requests.get(catalog['download_url'], timeout=30)
            response.raise_for_status()
            
            # Save .cat file
            with open(cat_file, 'wb') as f:
                f.write(response.content)
            
            print(f"✓ Downloaded {catalog['name']}")
            
            # Convert to JSON
            print("Converting to JSON...")
            convert_to_json(str(cat_file), str(json_file))
            
            return str(json_file)
        
        except requests.RequestException as e:
            print(f"Error downloading catalog: {e}")
            return None
    
    def list_catalogs(self):
        """List all available catalogs"""
        if not self.available_catalogs:
            print("Fetching available catalogs from GitHub...")
            self.fetch_available_catalogs()
        
        if not self.available_catalogs:
            print("Failed to fetch catalogs.")
            return
        
        print(f"\nAvailable Catalogs ({len(self.available_catalogs)}):")
        print("-" * 70)
        for i, cat in enumerate(self.available_catalogs, 1):
            cached = "✓" if (self.cache_dir / cat['name'].replace('.cat', '.json')).exists() else " "
            print(f"  {cached} {i:2}. {cat['display_name']}")
        print("\n(✓ = Already cached)")
    
    def get_cached_catalogs(self):
        """Get list of locally cached catalogs"""
        cached = []
        for json_file in self.cache_dir.glob("*.json"):
            cached.append({
                'name': json_file.stem,
                'path': str(json_file)
            })
        return cached
    
    def clear_cache(self):
        """Clear the catalog cache"""
        count = 0
        for file in self.cache_dir.glob("*"):
            file.unlink()
            count += 1
        print(f"Cleared {count} cached files.")


def get_catalog(catalog_name=None):
    """Main function to get a catalog (download if needed)"""
    downloader = CatalogDownloader()
    
    if not catalog_name:
        downloader.list_catalogs()
        return None
    
    return downloader.download_catalog(catalog_name)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python catalog_manager.py <catalog_name>")
        print("       python catalog_manager.py --list")
        print("       python catalog_manager.py --clear-cache")
        print("\nExample: python catalog_manager.py 'Space Marines'")
        sys.exit(1)
    
    downloader = CatalogDownloader()
    
    if sys.argv[1] == '--list':
        downloader.list_catalogs()
    elif sys.argv[1] == '--clear-cache':
        downloader.clear_cache()
    else:
        catalog_name = ' '.join(sys.argv[1:])
        json_file = downloader.download_catalog(catalog_name)
        if json_file:
            print(f"\n✓ Catalog ready: {json_file}")
