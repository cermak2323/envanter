#!/usr/bin/env python3
"""
Render Environment Variables Import Tool
.env.production dosyasından environment variables'ları parse eder
"""

def parse_env_file():
    """Parse .env.production file"""
    env_vars = {}
    
    try:
        with open('.env.production', 'r') as f:
            for line in f:
                line = line.strip()
                
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                
                # Parse KEY=VALUE
                if '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
        
        return env_vars
    except FileNotFoundError:
        print("❌ .env.production file not found!")
        return {}

def determine_scope(key):
    """Determine if variable should be Secret or Environment Variable"""
    secret_vars = [
        'DATABASE_URL',
        'B2_APPLICATION_KEY', 
        'SESSION_SECRET',
        'ADMIN_COUNT_PASSWORD'
    ]
    
    return "Secret" if key in secret_vars else "Environment Variable"

def generate_render_instructions():
    """Generate step-by-step Render instructions"""
    env_vars = parse_env_file()
    
    if not env_vars:
        return
    
    print("🚀 RENDER DASHBOARD IMPORT INSTRUCTIONS")
    print("=" * 60)
    print("1. Go to: https://dashboard.render.com")
    print("2. Select your service")
    print("3. Go to Environment tab")
    print("4. Add each variable below:")
    print()
    
    # Filter relevant variables for Render
    render_vars = {k: v for k, v in env_vars.items() 
                  if k not in ['FLASK_ENV', 'PYTHON_VERSION', 'RENDER', 'PORT']}
    
    for i, (key, value) in enumerate(render_vars.items(), 1):
        scope = determine_scope(key)
        scope_emoji = "🔐" if scope == "Secret" else "🔑"
        
        print(f"{scope_emoji} VARIABLE #{i}: {key}")
        print("-" * 40)
        print(f"Key: {key}")
        print(f"Value: {value}")
        print(f"Scope: {scope}")
        print()
    
    print("✅ VERIFICATION CHECKLIST:")
    print("- [ ] All 6 variables added")
    print("- [ ] Secret variables marked as Secret")
    print("- [ ] Values copied exactly (no extra spaces)")
    print("- [ ] Manual Deploy triggered")
    print()
    print("🧪 TEST: https://your-app.onrender.com/health")

def create_render_bulk_import():
    """Create bulk import format"""
    env_vars = parse_env_file()
    
    if not env_vars:
        return
    
    print("\n📋 BULK IMPORT FORMAT (Copy/Paste)")
    print("=" * 60)
    
    render_vars = {k: v for k, v in env_vars.items() 
                  if k not in ['FLASK_ENV', 'PYTHON_VERSION', 'RENDER', 'PORT']}
    
    for key, value in render_vars.items():
        scope = determine_scope(key)
        print(f"{key}={value} # {scope}")

if __name__ == "__main__":
    print("🔧 ENVANTER QR - RENDER ENVIRONMENT IMPORT")
    print()
    
    generate_render_instructions()
    create_render_bulk_import()
    
    print("\n" + "=" * 60)
    print("📂 File created: .env.production")
    print("🚀 Ready for Render deployment!")