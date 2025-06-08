# Slide2Thesis

A tool that automatically generates a thesis document from a PDF presentation using Google's Gemini API.

## Features

- Extract text and images from PDF slides
- Categorize slides into logical sections
- Generate thesis chapters from slide content
- Add citations and references
- Generate figures and tables
- Compile a complete thesis document in PDF format
- Web interface for easy uploading and processing

## System Architecture

The following flowchart illustrates the component flow and processing pipeline of Slide2Thesis:

```mermaid
flowchart TD
    A["📄 PDF Input<br/>(Presentation Slides)"] --> B["🔧 API Factory<br/>Create AI API Instance<br/>(Gemini/OpenAI)"]
    B --> C["📝 Text Extractor<br/>Extract text from PDF pages<br/>Output: extracted_text.txt"]
    C --> D["🏷️ Page Classifier<br/>Categorize pages into sections<br/>(Introduction, Methods, Results, etc.)"]
    D --> E["📚 Chapter Generator<br/>Generate thesis chapters<br/>from classified sections"]
    E --> F["📖 Citation Generator<br/>Add academic citations<br/>using PubMed API"]
    F --> G["🖼️ Figure Generator<br/>Add figure references<br/>and captions"]
    G --> H["📋 YAML Metadata Generator<br/>Generate thesis metadata<br/>(title, author, etc.)"]
    H --> I["🔨 Thesis Compiler<br/>Compile final PDF using<br/>Pandoc + Tectonic"]
    I --> J["📖 Final Thesis PDF"]

    subgraph "🌐 Web Interface"
        K["Flask App<br/>(app.py)"] --> L["Upload Interface"]
        L --> M["Background Processing"]
        M --> N["Job Status Tracking"]
        N --> O["Download Results"]
    end

    subgraph "💻 CLI Interface"
        P["Command Line<br/>(main.py)"] --> Q["Argument Parsing"]
        Q --> R["Step Selection<br/>(All or Individual)"]
    end

    subgraph "🔄 Processing Steps"
        C --> C1["Page 1: Text"]
        C --> C2["Page 2: Text"]
        C --> C3["Page N: Text"]
        
        D --> D1["introduction_section.txt"]
        D --> D2["methods_section.txt"]
        D --> D3["results_section.txt"]
        D --> D4["conclusions_section.txt"]
        
        E --> E1["introduction_chapter.md"]
        E --> E2["methods_chapter.md"]
        E --> E3["results_chapter.md"]
        E --> E4["conclusions_chapter.md"]
        
        F --> F1["*_chapter_cited.md"]
        F --> F2["references.bib"]
        
        G --> G1["*_chapter_with_figures.md"]
        G --> G2["Figure references"]
        
        H --> H1["thesis_metadata.yaml"]
        
        I --> I1["thesis.tex"]
        I --> I2["thesis.pdf"]
    end

    subgraph "🔌 External APIs"
        S["PubMed API<br/>(Citations)"]
        T["AI APIs<br/>(Gemini/OpenAI)"]
    end

    K --> A
    P --> A
    F --> S
    B --> T
    D --> T
    E --> T
    F --> T
    G --> T
    H --> T

    style A fill:#e1f5fe
    style J fill:#c8e6c9
    style K fill:#fff3e0
    style P fill:#f3e5f5
    style S fill:#ffebee
    style T fill:#e8f5e8
```

### Processing Pipeline

The system follows a 7-step pipeline:

1. **Text Extraction**: Extracts text content from each PDF page
2. **Page Classification**: Uses AI to categorize pages into thesis sections (Introduction, Methods, Results, etc.)
3. **Chapter Generation**: Converts classified content into well-structured thesis chapters
4. **Citation Addition**: Automatically adds relevant academic citations using PubMed API
5. **Figure Integration**: Adds figure references and captions to chapters
6. **Metadata Generation**: Creates YAML metadata for the thesis document
7. **Thesis Compilation**: Compiles everything into a final PDF using Pandoc and Tectonic

The system supports both web interface (Flask app) and command-line interface, with flexible AI provider support (Gemini/OpenAI).

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/ythuang0522/Slide2Thesis.git
   cd Slide2Thesis
   ```

2. Install required libraries:
   ```
   pip install -r requirements.txt
   ```

3. Install additional dependencies:
   ```
   conda install -c conda-forge pandoc
   conda install tectonic
   
   # For macOS
   brew install pandoc-crossref
   
   # For Linux (Debian/Ubuntu)
   sudo apt-get install pandoc-crossref
   
   # For Linux (Fedora/RHEL/CentOS)
   sudo dnf install pandoc-crossref
   
   # Alternative for any system: Install via cabal (Haskell package manager)
   cabal update
   cabal install pandoc-crossref
   ```

## Usage

### Web Interface

Start the web server:
```bash
python app.py
```

Then open your browser and navigate to http://127.0.0.1:5000 to access the web interface.

### Command Line Interface

Basic usage:
```bash
python main.py path/to/your/presentation.pdf
```

For specific steps:
```bash
# Extract text only
python main.py path/to/your/presentation.pdf --extract-text

# Generate chapters only
python main.py path/to/your/presentation.pdf --generate-chapters

# Add citations only
python main.py path/to/your/presentation.pdf --add-citations

# Compile the final thesis
python main.py path/to/your/presentation.pdf --compile
```

## Project Structure

- `main.py`: Main script orchestrating the thesis generation process
- `app.py`: Flask web application for the web interface
- `templates/`: HTML templates for the web interface
- `text_extractor.py`: Extracts text from PDF presentations
- `page_classifier.py`: Categorizes pages into logical sections
- `chapter_generator.py`: Generates thesis chapters
- `citation_generator.py`: Adds relevant citations
- `figure_generator.py`: Processes and references figures
- `yaml_metadata_generator.py`: Creates YAML metadata
- `thesis_compiler.py`: Compiles the final thesis document
- `gemini_api.py`: Wrapper for Google's Gemini API

## Testing

Before running the tests, install the development dependencies:

```bash
pip install -r requirements-dev.txt
```

The project uses `pytest`. Run the test suite with:

```bash
pytest
```

## License

MIT

## Author

Yao-Ting Huang (@ythuang0522) 