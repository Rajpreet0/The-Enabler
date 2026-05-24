import json
import sys
from pathlib import Path
import pytest

# =====================================================================
# 1. SETUP & PATHS
# =====================================================================
# This line tells PY where to find your main application code ('app')
# It adds the parent folder to Python's search path so import work correctly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.masking import mask_text

# Define where the test files are located relative to this script
DOCS_DIR = Path(__file__).parent / "documents"      # Folder containing cv.txt, invoice.txt, etc. 
ANNO_DIR = Path(__file__).parent / "annotations"    # Folder containing cv.json, invoice.json, etc.

# =====================================================================
# 2. FIXTURES (Setup Helpers for Tests)
# =====================================================================
# In pytest, a "fixture" is a setup function that prepares tools or data for your tests.
# 'scope="session"' means this runs only ONCE when you start the test suite, not for every single file.
@pytest.fixture(scope="session", autouse=True)
def warm_engines():
    """
        Spins up the AI models / PII engines immediately before any tests start.
        'autouse=True' means it runs automatically in the background
    """
    from app.masking.engines import get_engines
    get_engines()

@pytest.fixture(scope="session")
def pipeline(warm_engines):
    """
        A reusable helper function to run your PII pipeline.
        It reads a text file (e.g., 'cv.txt'), processes it for German PII, 
        and returns a list of all the secrets it found.
    """
    def _run(doc_name: str) -> list[dict]:
        # Read the text file
        text  = (DOCS_DIR / doc_name).read_text(encoding="utf-8")
        # Run your German PII masking pipeline
        result = mask_text(text, language="de")
        # Return only the extracted entities (predicitons)
        return result.entities_found
    return _run

@pytest.fixture(scope="session")
def annotation():
    """
        A reusable helper function to load your "Ground Truth" (the correct answers).
        If you give it 'cv.txt', it will look for 'cv.json' in the annotations folder
        and read the correct PII entities you manually labeled.
    """
    def _load(doc_name: str) -> list[dict]:
        stem = Path(doc_name).stem                  # Remove '.txt' extension (e.g., 'cv.txt' -> 'cv')
        anno_path = ANNO_DIR / f"{stem}.json"       # Creates 'cv.json' path
        
        # Open the JSON file and extract the expected entities list
        data = json.loads(anno_path.read_text(encoding="utf-8"))
        return data["entities"]
    return _load

# =====================================================================
# 3. UTILITY FUNCTIONS
# =====================================================================
def pytest_collect_file(parent, file_path):
    """
        A special pytest hook. Currently left blank ('pass'), meaning it does nothing.
    """
    pass

def all_doc_names() -> list[str]:
    """
    Scans your 'documents' folder, finds all '.txt' files, 
    sorts them alphabetically, and returns their names as a list.
    Example output: ['cv.txt', 'employment_contract.txt', 'invoice.txt']
    """
    return [p.name for p in sorted(DOCS_DIR.glob("*.txt"))]
