import sys, types

mods = {
    'PIL': types.ModuleType('PIL'),
    'PIL.Image': types.ModuleType('PIL.Image'),
    'tenacity': types.ModuleType('tenacity'),
    'tenacity.retry': types.ModuleType('tenacity.retry'),
    'tenacity.stop': types.ModuleType('tenacity.stop'),
    'tenacity.wait': types.ModuleType('tenacity.wait'),
    'google': types.ModuleType('google'),
    'google.genai': types.ModuleType('google.genai'),
    'fitz': types.ModuleType('fitz'),
    'dotenv': types.ModuleType('dotenv'),
    'Bio': types.ModuleType('Bio'),
    'Bio.Entrez': types.ModuleType('Bio.Entrez'),
}

for name, module in mods.items():
    if name not in sys.modules:
        sys.modules[name] = module

# Provide minimal attributes used in the code
sys.modules['PIL.Image'].Image = object
sys.modules['tenacity'].retry = lambda *a, **k: (lambda f: f)
sys.modules['tenacity'].stop_after_attempt = lambda *a, **k: None
sys.modules['tenacity'].wait_exponential = lambda *a, **k: None
sys.modules['dotenv'].load_dotenv = lambda *a, **k: None

class DummyModel:
    def generate_content(self, *a, **k):
        class R:
            text = ""
        return R()

class DummyClient:
    def __init__(self, *a, **k):
        self.models = DummyModel()

sys.modules['google.genai'].Client = DummyClient
