#!/usr/bin/env python3

import fitz
import re
import os
import json
from collections import Counter
import glob

def process_pdf_production(pdf_path):
    print(f"Processing: {pdf_path}")
    
    doc = fitz.open(pdf_path)
    
    title = extract_title_comprehensive(doc)
    
    spans = gather_spans_production(doc)
    
    headings = extract_headings_final(spans, title)
    
    result = {
        "title": title,
        "outline": headings
    }
    
    doc.close()
    return result

def extract_title_comprehensive(doc):
    if not doc or doc.page_count == 0:
        return ""
    
    first_page = doc[0]
    page_height = first_page.rect.height
    top_section = page_height * 0.4
    
    blocks = first_page.get_text("dict")["blocks"]
    title_candidates = []
    
    for block in blocks:
        if "lines" not in block:
            continue
        
        for line in block["lines"]:
            if line["bbox"][1] > top_section:
                continue
                
            for span in line["spans"]:
                text = span["text"].strip()
                size = span["size"]
                bbox = span["bbox"]
                
                if text and len(text) > 2 and size >= 10:
                    title_candidates.append({
                        "text": text,
                        "size": size,
                        "bbox": bbox,
                        "y": bbox[1]
                    })
    
    if not title_candidates:
        all_text_spans = []
        for page_num in range(min(2, doc.page_count)):
            page = doc[page_num]
            page_blocks = page.get_text("dict")["blocks"]
            for block in page_blocks:
                if "lines" not in block:
                    continue
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if text and len(text) > 5:
                            all_text_spans.append(text)
        
        return ""
    
    max_size = max(c["size"] for c in title_candidates)
    
    size_threshold = max_size - 2.0
    max_size_candidates = [c for c in title_candidates if c["size"] >= size_threshold]
    
    max_size_candidates.sort(key=lambda x: x["y"])
    
    title_groups = []
    current_group = []
    
    for candidate in max_size_candidates:
        if not current_group:
            current_group.append(candidate)
        else:
            y_diff = abs(candidate["y"] - current_group[-1]["y"])
            if y_diff < 20:
                current_group.append(candidate)
            else:
                if current_group:
                    title_groups.append(current_group)
                current_group = [candidate]
    
    if current_group:
        title_groups.append(current_group)
    
    if title_groups:
        title_group = title_groups[0]
        title_group.sort(key=lambda x: x["bbox"][0])
        
        title_parts = [c["text"] for c in title_group]
        title = ' '.join(title_parts)
        
        title = clean_title(title)
        return title if title else ""
    
    return ""

def clean_title(title):
    if not title:
        return ""
    
    title = re.sub(r'\s+', ' ', title).strip()
    
    title = re.sub(r'[,;:]+$', '', title)
    
    words = title.split()
    if len(words) >= 4:
        half = len(words) // 2
        first_half = ' '.join(words[:half])
        second_half = ' '.join(words[half:])
        
        if first_half == second_half:
            return first_half
    
    return title

def gather_spans_production(doc):
    items = []
    
    for page_num in range(doc.page_count):
        page = doc[page_num]
        blocks = page.get_text("dict")["blocks"]
        page_items = []
        
        for block in blocks:
            if "lines" not in block:
                continue
            
            line_groups = {}
            for line in block["lines"]:
                y_key = round(line["bbox"][1])
                if y_key not in line_groups:
                    line_groups[y_key] = []
                line_groups[y_key].append(line)
            
            for y_pos, lines in line_groups.items():
                all_spans = []
                for line in lines:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if text and not is_decorative_text(text) and not is_likely_link(text):
                            all_spans.append(span)
                
                if not all_spans:
                    continue
                
                span_groups = [all_spans]
                
                for span_group in span_groups:
                    line_spans_by_y = {}
                    
                    for span in span_group:
                        text = span["text"].strip()
                        if text and not is_decorative_text(text) and not is_likely_link(text):
                            y_pos = round(span["bbox"][1], 1)
                            if y_pos not in line_spans_by_y:
                                line_spans_by_y[y_pos] = []
                            line_spans_by_y[y_pos].append(span)
                    
                    for y_pos, line_spans in line_spans_by_y.items():
                        if len(line_spans) == 1:
                            span = line_spans[0]
                            text = span["text"].strip()
                            if len(text) > 1:
                                page_items.append({
                                    "text": text,
                                    "size": span["size"],
                                    "page": page_num,
                                    "bbox": span["bbox"]
                                })
                        else:
                            line_spans.sort(key=lambda s: s["bbox"][0])
                            
                            combined_text = ""
                            for i, span in enumerate(line_spans):
                                text_part = span["text"].strip()
                                if i == 0:
                                    combined_text = text_part
                                else:
                                    prev_span = line_spans[i-1]
                                    curr_span = span
                                    
                                    gap = curr_span["bbox"][0] - prev_span["bbox"][2]
                                    
                                    if gap <= 2.8:
                                        combined_text += text_part
                                    else:
                                        combined_text += " " + text_part
                            
                            combined_text = combined_text.strip()
                            
                            if len(combined_text) > 1:
                                max_size = max(s["size"] for s in line_spans)
                                min_x0 = min(s["bbox"][0] for s in line_spans)
                                min_y0 = min(s["bbox"][1] for s in line_spans)
                                max_x1 = max(s["bbox"][2] for s in line_spans)
                                max_y1 = max(s["bbox"][3] for s in line_spans)
                                
                                page_items.append({
                                    "text": combined_text,
                                    "size": max_size,
                                    "page": page_num,
                                    "bbox": [min_x0, min_y0, max_x1, max_y1]
                                })
        
        items.extend(page_items)
    
    return items

def is_decorative_text(text):
    return (re.match(r'^[.\-_=\s]{3,}$', text) or 
            len(set(text.strip().replace(' ', ''))) <= 2 or
            re.search(r'(https?://|www\.|@.*\.com)', text.lower()))

def is_likely_link(text):
    text = text.strip().lower()
    
    url_patterns = [
        r'https?://',
        r'www\.',
        r'ftp://',
        r'mailto:',
        r'\.com\b',
        r'\.org\b',
        r'\.net\b',
        r'\.edu\b',
        r'\.gov\b',
        r'@\w+\.',
    ]
    
    for pattern in url_patterns:
        if re.search(pattern, text):
            return True
    
    return False

def detect_significant_gaps_and_split(spans_in_line):
    if len(spans_in_line) <= 1:
        return [spans_in_line]
    
    sorted_spans = sorted(spans_in_line, key=lambda s: s.get("bbox", [0])[0])
    
    gaps = []
    for i in range(len(sorted_spans) - 1):
        curr_span = sorted_spans[i]
        next_span = sorted_spans[i + 1]
        
        curr_bbox = curr_span.get("bbox", [0, 0, 0, 0])
        next_bbox = next_span.get("bbox", [0, 0, 0, 0])
        
        gap = next_bbox[0] - curr_bbox[2]
        gaps.append(gap)
    
    if gaps:
        median_gap = sorted(gaps)[len(gaps) // 2]
        threshold = max(median_gap * 3, 20)
    else:
        return [spans_in_line]
    
    groups = []
    current_group = [sorted_spans[0]]
    
    for i, gap in enumerate(gaps):
        if gap > threshold:
            groups.append(current_group)
            current_group = [sorted_spans[i + 1]]
        else:
            current_group.append(sorted_spans[i + 1])
    
    if current_group:
        groups.append(current_group)
    
    return groups

def merge_fragments_by_proximity(items):
    if not items:
        return items
    
    items.sort(key=lambda x: (x["bbox"][1], x["bbox"][0]))
    
    size_groups = {}
    for item in items:
        rounded_size = round(item["size"] * 2) / 2
        if rounded_size not in size_groups:
            size_groups[rounded_size] = []
        size_groups[rounded_size].append(item)
    
    merged_items = []
    
    for size, group in size_groups.items():
        if len(group) == 1:
            merged_items.extend(group)
            continue
        
        group.sort(key=lambda x: (x["bbox"][1], x["bbox"][0]))
        
        i = 0
        while i < len(group):
            current = group[i]
            candidates = [current]
            
            j = i + 1
            while j < len(group):
                next_item = group[j]
                
                y_distance = abs(next_item["bbox"][1] - current["bbox"][3])
                x_distance = abs(next_item["bbox"][0] - current["bbox"][2])
                
                should_merge = (
                    y_distance < 5 and
                    x_distance < 10 and
                    (
                        (len(current["text"].strip()) == 1 and len(next_item["text"].strip()) <= 3) or
                        (current["text"].strip().endswith('-') and len(current["text"].strip()) <= 4)
                    )
                )
                
                if should_merge:
                    candidates.append(next_item)
                    current = next_item
                    j += 1
                else:
                    break
            
            if len(candidates) > 1:
                merged_text = conservative_merge_text_fragments([c["text"] for c in candidates])
                
                max_size = max(c["size"] for c in candidates)
                min_x0 = min(c["bbox"][0] for c in candidates)
                min_y0 = min(c["bbox"][1] for c in candidates)
                max_x1 = max(c["bbox"][2] for c in candidates)
                max_y1 = max(c["bbox"][3] for c in candidates)
                
                merged_items.append({
                    "text": merged_text,
                    "size": max_size,
                    "page": candidates[0]["page"],
                    "bbox": [min_x0, min_y0, max_x1, max_y1]
                })
            else:
                merged_items.append(current)
            
            i += len(candidates)
    
    return merged_items

def conservative_merge_text_fragments(texts):
    if not texts:
        return ""
    
    if len(texts) == 1:
        return texts[0].strip()
    
    cleaned = [t.strip() for t in texts if t.strip()]
    
    if len(cleaned) <= 2:
        return ' '.join(cleaned)
    
    result = []
    for text in cleaned:
        if not result:
            result.append(text)
            continue
        
        prev = result[-1]
        
        should_join_no_space = (
            (len(prev) == 1 and prev.isalpha() and 
             len(text) <= 6 and text.startswith(prev.lower())) or
            (prev.endswith('-') and len(prev) <= 4 and len(text) <= 6)
        )
        
        if should_join_no_space:
            result[-1] = prev + text
        else:
            result.append(text)
    
    return ' '.join(result).strip()

def extract_headings_final(spans, title_text=""):
    if not spans:
        return []
    
    level_map, body_text_size = analyze_font_structure(spans)
    
    if not level_map:
        return []
    
    headings = []
    processed = set()
    
    for span in spans:
        text = span["text"].strip()
        
        if not text or text in processed:
            continue
        
        if title_text and (text == title_text.strip() or text in title_text or title_text in text):
            continue
        
        if is_likely_link(text):
            continue
        
        if not is_significant_heading(text, span["size"], body_text_size):
            continue
        
        heading_level = None
        min_diff = float('inf')
        
        for size, level in level_map.items():
            diff = abs(span["size"] - size)
            if diff < min_diff and diff < 1.5:
                heading_level = level
                min_diff = diff
        
        if heading_level and span["size"] > body_text_size + 0.1:
            headings.append({
                "text": text,
                "level": heading_level,
                "page": span["page"]
            })
            processed.add(text)
    
    filtered_headings = []
    for heading in headings:
        if is_high_quality_heading(heading["text"]):
            filtered_headings.append(heading)
    
    return filtered_headings

def merge_related_headings(headings):
    if len(headings) <= 1:
        return headings
    
    merged = []
    i = 0
    
    while i < len(headings):
        current = headings[i]
        candidates = [current]
        
        j = i + 1
        while j < len(headings):
            next_heading = headings[j]
            
            should_merge = (
                current["page"] == next_heading["page"] and
                current["level"] == next_heading["level"] and
                (
                    (current["text"].endswith(('-', 'for', 'the', 'to', 'of')) and
                     len(current["text"]) < 15 and len(next_heading["text"]) < 15 and
                     not next_heading["text"].startswith(('1.', '2.', '3.', '4.', 'Phase', 'Appendix')))
                )
            )
            
            if should_merge:
                candidates.append(next_heading)
                j += 1
            else:
                break
        
        if len(candidates) > 1:
            combined_text = ' '.join(c["text"] for c in candidates)
            
            merged.append({
                "level": current["level"],
                "text": combined_text,
                "page": current["page"]
            })
        else:
            merged.append(current)
        
        i += len(candidates)
    
    return merged

def analyze_font_structure(spans):
    font_sizes = [s["size"] for s in spans]
    size_counts = Counter(font_sizes)
    
    body_text_size = size_counts.most_common(1)[0][0] if size_counts else 12
    
    size_frequency = size_counts.most_common()
    
    heading_sizes = []
    for size, count in size_frequency:
        if size > body_text_size + 0.1:
            heading_sizes.append(size)
    
    heading_sizes.sort(reverse=True)
    
    level_map = {}
    prev_size = None
    level = 1
    
    for size in heading_sizes[:4]:
        if prev_size is None or prev_size - size >= 0.5:
            level_map[size] = level
            level += 1
            prev_size = size
        elif prev_size is not None:
            level_map[size] = level - 1
    
    return level_map, body_text_size

def is_significant_heading(text, font_size, body_text_size):
    if font_size <= body_text_size + 0.1:
        return False
    
    if not re.search(r'[a-zA-Z]', text):
        return False
    
    if len(text) < 3:
        return False
    
    if is_likely_link(text):
        return False
    
    if re.match(r'^[•·▪▫]\s+', text):
        return False
    
    if text.lower().startswith(('mission statement:', 'goals:')):
        return False
    
    if (re.match(r'^\d+\.', text) or 
        text.lower().startswith(('appendix', 'phase', 'for each', 'for the')) or
        text.lower() in ['table of contents', 'acknowledgements', 'revision history', 'references', 
                         'summary', 'background', 'timeline', 'milestones', 'approach', 'evaluation',
                         'preamble', 'membership', 'term', 'chair', 'meetings']):
        return True
    
    if text.strip().endswith(':'):
        return True
    
    letters = len(re.findall(r'[a-zA-Z]', text))
    if letters < len(text) * 0.2:
        return False
    
    return True

def is_high_quality_heading(text):
    if len(text) < 3:
        return False
    
    if text.count(' ') == 0:
        common_heading_words = ['introduction', 'overview', 'references', 'acknowledgements', 'contents', 'syllabus']
        if len(text) < 6 and text.lower() not in common_heading_words:
            return False
    
    if re.match(r'^[^\w\s]*$', text):
        return False
    
    return True

if __name__ == "__main__":
    import sys
    
    print("Starting production PDF processing...")
    
    input_dir = "/app/input"
    output_dir = "/app/output"
    
    if not os.path.exists(input_dir):
        print("Docker input directory not found, using local paths...")
        input_dir = "Challenge_1a/sample_dataset/pdfs"
        output_dir = "Challenge_1a/production_outputs"
    
    os.makedirs(output_dir, exist_ok=True)
    
    pdf_files = glob.glob(os.path.join(input_dir, "*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in {input_dir}")
        sys.exit(1)
    
    print(f"Found {len(pdf_files)} PDF files to process")
    
    for pdf_file in sorted(pdf_files):
        try:
            result = process_pdf_production(pdf_file)
            
            formatted_outline = []
            for heading in result["outline"]:
                formatted_outline.append({
                    "level": f"H{heading['level']}",
                    "text": heading["text"],
                    "page": heading["page"]
                })
            
            result["outline"] = formatted_outline
            
            basename = os.path.basename(pdf_file).replace('.pdf', '.json')
            output_file = os.path.join(output_dir, basename)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            print(f"Processed '{pdf_file}' -> '{output_file}'")
            
        except Exception as e:
            print(f"Error processing {pdf_file}: {e}")
            continue 
    
    print("Processing complete!")
  
