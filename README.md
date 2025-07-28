# Adobe India Hackathon 2025 - Round 1a solution

## Overview

This solution provides an intelligent PDF processing system that extracts titles and heading hierarchies from PDF documents. It processes all PDFs from an input directory and generates corresponding JSON files with extracted metadata.

## Approach

### 1. Title Extraction

- **Top Section Analysis**: Focuses on the top 40% of the first page to identify potential title candidates
- **Font Size Prioritization**: Identifies the largest font sizes as likely title text
- **Vertical Grouping**: Groups text elements that appear on similar vertical positions
- **Smart Reconstruction**: Combines fragmented title text while preserving original formatting

### 2. Text Span Processing

- **Line-based Grouping**: Groups text spans by their vertical position to maintain line integrity
- **Gap-based Joining**: Uses intelligent gap analysis to determine whether spans should be joined with or without spaces
- **Fragment Preservation**: Maintains original text exactly as it appears in the PDF, preventing text corruption
- **Link and Decoration Filtering**: Excludes URLs, email addresses, and decorative elements

### 3. Heading Detection

- **Font Structure Analysis**: Analyzes the distribution of font sizes throughout the document to establish heading hierarchy
- **Multi-level Classification**: Supports up to 4 heading levels (H1-H4) based on relative font sizes
- **Content Validation**: Filters headings based on content quality, length, and structural patterns
- **Duplicate Prevention**: Ensures headings don't duplicate the main title

### 4. Key Features

- **Text Integrity**: Preserves original text spacing and formatting (e.g., "HOPE To SEE You THERE!" remains unchanged)
- **Robust Error Handling**: Continues processing even if individual PDFs fail
- **Docker Compatibility**: Automatically detects container environment vs. local execution
- **Scalable Processing**: Efficiently handles multiple PDFs in batch mode

## Libraries Used

- **PyMuPDF (fitz)**: Primary PDF parsing and text extraction library
  - Provides detailed text positioning and font information
  - Enables precise bounding box analysis for gap detection
- **re**: Regular expressions for text pattern matching and validation
- **json**: JSON output formatting
- **collections.Counter**: Font size frequency analysis
- **glob**: File pattern matching for PDF discovery
- **os**: File system operations and path handling

## Technical Implementation

### Gap Analysis Algorithm

The solution uses a sophisticated gap analysis approach:

- Calculates horizontal distances between text spans
- Uses a threshold of 2.8 points to distinguish between broken words and separate words
- Joins spans without spaces for gaps ≤ 2.8 points (broken words)
- Joins spans with spaces for gaps > 2.8 points (separate words)

### Font Hierarchy Detection

- Identifies the most common font size as body text
- Finds font sizes larger than body text for heading classification
- Assigns heading levels based on relative size differences
- Filters headings that are only marginally larger than body text

### Quality Filtering

- Minimum length requirements for headings
- Link and URL detection and exclusion
- Decorative text pattern recognition
- Content-based validation (excludes bullet points, keeps numbered sections)

## Building and Running the Solution

### Expected Execution (Docker)

1. **Build the Docker image:**

```bash
docker build --platform linux/amd64 -t mysolutionname:somerandomidentifier .
```

2. **Run the solution:**

```bash
docker run --rm -v $(pwd)/input:/app/input -v $(pwd)/output:/app/output --network none mysolutionname:somerandomidentifier
```

### Container Behavior

- Automatically processes all PDFs from `/app/input` directory
- Generates corresponding `filename.json` files in `/app/output` for each `filename.pdf`
- Produces structured JSON output with title and outline hierarchy
- Handles processing errors gracefully without stopping the entire batch

### Local Development

For local testing and development:

1. **Install dependencies:**

```bash
pip install PyMuPDF
```

2. **Run locally:**

```bash
python production_solution.py
```

The script automatically detects the environment:

- In Docker: Uses `/app/input` and `/app/output` directories
- Locally: Uses `Challenge_1a/sample_dataset/pdfs` and `Challenge_1a/production_outputs`

## Output Format

Each processed PDF generates a JSON file with the following structure:

```json
{
  "title": "Document Title",
  "outline": [
    {
      "level": "H1",
      "text": "Main Heading",
      "page": 1
    },
    {
      "level": "H2",
      "text": "Sub Heading",
      "page": 2
    }
  ]
}
```

### Output Fields

- **title**: Main document title (empty string if no title detected)
- **outline**: Array of heading objects
  - **level**: Heading hierarchy level (H1, H2, H3, H4)
  - **text**: Exact heading text as it appears in the PDF
  - **page**: Zero-indexed page number where the heading appears

## Performance Characteristics

- **Text Preservation**: Maintains original text formatting and spacing
- **Memory Efficient**: Processes documents page by page
- **Error Resilient**: Continues processing if individual documents fail
- **Scalable**: Handles multiple documents in batch mode
- **Fast Processing**: Optimized for production workloads

## Error Handling

The solution includes comprehensive error handling:

- Individual PDF processing errors don't stop the batch
- Graceful fallback for documents without clear titles
- Robust handling of malformed or encrypted PDFs
- Detailed logging for debugging and monitoring
