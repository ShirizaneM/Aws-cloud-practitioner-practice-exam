#!/usr/bin/env python3
"""
Parse AWS CLF-C02 Practice Questions from PDF text extraction
"""

import json
import re
from pathlib import Path

def parse_question_blocks(text):
    """Parse questions from the extracted text"""
    questions = []
    
    # Split by question patterns - handles both "Question #XTopic 1" and "Question #X Topic 1"
    blocks = re.split(r'Question #(\d+)(?:Topic \d+)?', text)
    
    # Skip the first block (header before first question)
    for i in range(1, len(blocks), 2):
        q_num = int(blocks[i])
        q_text = blocks[i+1] if i+1 < len(blocks) else ""
        
        # Clean up the text
        q_text = q_text.strip()
        
        # Extract question - get text before options
        question_match = re.search(r'^([^A-Z]*(?:[A-Z]\.).*?)(?=A\.|B\.|C\.|D\.|Correct Answer:)', q_text, re.DOTALL)
        if question_match:
            question_text = question_match.group(1).strip()
        else:
            # Try simpler pattern
            q_match = re.search(r'^(.*?)(?=A\.)', q_text, re.DOTALL)
            question_text = q_match.group(1).strip() if q_match else q_text[:200]
        
        # Clean up question text
        question_text = re.sub(r'\s+', ' ', question_text).strip()
        
        # Extract options
        options = []
        opt_pattern = r'([A-D])\.\s*([^\n]*?)(?=\s*[A-D]\.|\s*Correct Answer:|\s*#\s*Correct Answer:|\s*Community vote|$)'
        matches = re.findall(opt_pattern, q_text, re.DOTALL)
        
        if matches:
            for opt, ans in matches:
                ans = re.sub(r'\s+', ' ', ans).strip()
                options.append(f"{opt}. {ans}")
        
        # If no options found, try simpler pattern
        if not options:
            for letter in ['A', 'B', 'C', 'D']:
                match = re.search(rf'{letter}\.\s*([^\n]*(?:\n(?!A\.|B\.|C\.|D\.|Correct Answer)[^\n]*)*)', q_text, re.DOTALL)
                if match:
                    ans = re.sub(r'\s+', ' ', match.group(1)).strip()
                    options.append(f"{letter}. {ans}")
        
        # Extract correct answer
        correct_match = re.search(r'(?:#\s*)?Correct Answer:\s*([A-D]+)', q_text, re.DOTALL)
        correct_answer = correct_match.group(1) if correct_match else ""
        
        # Extract community vote
        community_vote = "Not available"
        vote_match = re.search(r'Community vote distribution.*?([A-D])\s*\((\d+)%\)', q_text, re.DOTALL)
        if vote_match:
            community_vote = f"{vote_match.group(1)} ({vote_match.group(2)}%)"
        else:
            vote_match2 = re.search(r'<table>([A-D])\s*\((\d+)%\)', q_text, re.DOTALL)
            if vote_match2:
                community_vote = f"{vote_match2.group(1)} ({vote_match2.group(2)}%)"
        
        # Determine domain based on question content
        domain = "General"
        q_lower = question_text.lower()
        if any(x in q_lower for x in ['s3', 'storage', 'glacier', 'ebs', 'efs', 'backup']):
            domain = "Storage"
        elif any(x in q_lower for x in ['ec2', 'compute', 'lambda', 'instance', 'fargate', 'container']):
            domain = "Compute"
        elif any(x in q_lower for x in ['security', 'iam', 'shared responsibility', 'trusted advisor', 'inspector', 'guardduty', 'macie', 'waf', 'shield']):
            domain = "Security"
        elif any(x in q_lower for x in ['database', 'rds', 'dynamodb', 'aurora', 'redshift', 'nosql']):
            domain = "Database"
        elif any(x in q_lower for x in ['vpc', 'network', 'connect', 'route 53', 'cloudfront', 'direct connect', 'vpn']):
            domain = "Networking"
        elif any(x in q_lower for x in ['cost', 'pricing', 'budget', 'billing', 'reserved instance', 'savings plan']):
            domain = "Billing & Pricing"
        elif any(x in q_lower for x in ['cloud', 'aws', 'well-architected', 'caf', 'cloud adoption']):
            domain = "Cloud Concepts"
        
        # Extract topic from first sentence
        topic = question_text.split('.')[0] if question_text else ""
        if len(topic) > 100:
            topic = question_text[:100]
        
        if question_text and options:
            questions.append({
                "id": q_num,
                "topic": topic[:100],
                "question": question_text[:500],
                "options": options[:4],
                "correct_answer": correct_answer,
                "community_vote": community_vote,
                "domain": domain
            })
    
    return questions

def generate_flashcards(questions):
    """Generate interactive HTML flashcards from questions"""
    html = """<!DOCTYPE html>
<html>
<head>
    <title>AWS CLF-C02 Practice Exam</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; background: #f0f2f5; }
        .header { background: #232f3e; color: white; padding: 20px; border-radius: 12px; margin-bottom: 20px; text-align: center; }
        .header h1 { color: #ff9900; margin: 0; }
        .stats { display: flex; justify-content: center; gap: 10px; flex-wrap: wrap; margin: 10px 0; }
        .badge { background: #ff9900; color: #232f3e; padding: 5px 12px; border-radius: 20px; font-weight: bold; font-size: 14px; }
        .card { background: white; padding: 20px; margin: 15px 0; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
        .question { font-size: 17px; font-weight: 600; color: #232f3e; margin-bottom: 12px; line-height: 1.5; }
        .options { margin: 10px 0; }
        .option { padding: 8px 10px; margin: 4px 0; background: #f8f9fa; border-radius: 6px; border-left: 3px solid #ff9900; }
        .domain-tag { display: inline-block; background: #232f3e; color: white; padding: 2px 10px; border-radius: 12px; font-size: 11px; }
        .vote-tag { display: inline-block; background: #e8f5e9; color: #2e7d32; padding: 2px 10px; border-radius: 12px; font-size: 11px; margin-left: 5px; }
        .answer { display: none; margin-top: 10px; padding: 15px; background: #e8f5e9; border-radius: 8px; border-left: 4px solid #4caf50; }
        .answer.show { display: block; }
        .btn { background: #232f3e; color: white; border: none; padding: 8px 20px; border-radius: 6px; cursor: pointer; font-size: 14px; transition: all 0.3s; margin: 3px; }
        .btn:hover { background: #ff9900; color: #232f3e; }
        .btn-green { background: #4caf50; }
        .btn-red { background: #f44336; }
        .nav { display: flex; justify-content: center; align-items: center; gap: 10px; margin: 15px 0; flex-wrap: wrap; }
        .search { width: 100%; padding: 10px; border: 2px solid #ddd; border-radius: 6px; font-size: 15px; margin: 10px 0; }
        .search:focus { outline: none; border-color: #ff9900; }
        .progress { position: fixed; top: 0; left: 0; height: 3px; background: #ff9900; transition: width 0.3s; z-index: 1000; }
        .controls { display: flex; justify-content: center; gap: 5px; flex-wrap: wrap; margin: 10px 0; }
        .filter-btn { background: #e0e0e0; color: #333; border: none; padding: 5px 12px; border-radius: 15px; cursor: pointer; font-size: 12px; }
        .filter-btn.active { background: #ff9900; color: #232f3e; }
    </style>
</head>
<body>
    <div class="progress" id="progressBar" style="width:0%"></div>
    
    <div class="header">
        <h1>📚 AWS CLF-C02 Practice Exam</h1>
        <p>AWS Certified Cloud Practitioner - Practice Questions</p>
    </div>
    
    <div class="stats" id="stats"></div>
    
    <div>
        <input class="search" id="searchInput" placeholder="🔍 Search questions..." onkeyup="filterQuestions()">
    </div>
    
    <div class="controls" id="domainFilters">
        <button class="filter-btn active" onclick="filterByDomain('all')">All</button>
    </div>
    
    <div id="cards"></div>
    
    <div class="nav">
        <button class="btn" onclick="prevPage()">⬅ Previous</button>
        <span id="pageInfo"></span>
        <button class="btn" onclick="nextPage()">Next ➡</button>
    </div>

    <script>
        const allQuestions = """ + json.dumps(questions) + """;
        let currentPage = 0;
        const perPage = 5;
        let answered = {};
        let currentFilter = 'all';
        let filteredQuestions = [...allQuestions];

        function renderQuestions(questions) {
            const container = document.getElementById('cards');
            const start = currentPage * perPage;
            const end = Math.min(start + perPage, questions.length);
            const pageQuestions = questions.slice(start, end);
            
            if (pageQuestions.length === 0) {
                container.innerHTML = '<p style="text-align:center;padding:30px;">No questions found.</p>';
                return;
            }
            
            let html = '';
            pageQuestions.forEach(q => {
                const isAnswered = answered[q.id] !== undefined;
                html += `<div class="card">`;
                html += `<div class="question">Q${q.id}: ${q.question}</div>`;
                html += `<div class="options">`;
                if (q.options && q.options.length > 0) {
                    q.options.forEach(opt => {
                        html += `<div class="option">${opt}</div>`;
                    });
                }
                html += `</div>`;
                html += `<span class="domain-tag">${q.domain || 'General'}</span>`;
                if (q.community_vote && q.community_vote !== 'Not available') {
                    html += `<span class="vote-tag">📊 ${q.community_vote}</span>`;
                }
                html += `<br><br>`;
                html += `<button class="btn" onclick="toggleAnswer(${q.id})">Show Answer</button>`;
                if (isAnswered) {
                    html += `<span style="margin-left:10px;color:${answered[q.id] ? 'green' : 'red'};">
                        ${answered[q.id] ? '✅ Correct' : '❌ Incorrect'}
                    </span>`;
                }
                html += `<div class="answer" id="answer-${q.id}">`;
                html += `<strong>✅ Answer: ${q.correct_answer}</strong><br>`;
                html += `<div style="margin-top:5px;">`;
                html += `<button class="btn btn-green" onclick="markCorrect(${q.id})">✓ Correct</button>`;
                html += `<button class="btn btn-red" onclick="markIncorrect(${q.id})">✗ Incorrect</button>`;
                html += `</div>`;
                html += `</div>`;
                html += `</div>`;
            });
            
            container.innerHTML = html;
            updateStats(questions);
        }

        function toggleAnswer(id) {
            const el = document.getElementById(`answer-${id}`);
            if (el) el.classList.toggle('show');
        }

        function markCorrect(id) { answered[id] = true; renderQuestions(filteredQuestions); }
        function markIncorrect(id) { answered[id] = false; renderQuestions(filteredQuestions); }

        function updateStats(questions) {
            const total = questions.length;
            const answeredCount = Object.keys(answered).filter(id => answered[id] !== undefined).length;
            document.getElementById('stats').innerHTML = `
                <span class="badge">📝 ${total} Questions</span>
                <span class="badge">✅ ${answeredCount} Answered</span>
                <span class="badge">🎯 Multiple Choice</span>
            `;
            const progress = total > 0 ? (answeredCount / total * 100) : 0;
            document.getElementById('progressBar').style.width = progress + '%';
            document.getElementById('pageInfo').textContent = `Page ${currentPage + 1} of ${Math.ceil(questions.length / perPage) || 1}`;
        }

        function filterQuestions() {
            const search = document.getElementById('searchInput').value.toLowerCase();
            filteredQuestions = allQuestions.filter(q => {
                const matchDomain = currentFilter === 'all' || q.domain === currentFilter;
                const matchSearch = q.question.toLowerCase().includes(search) || 
                                   (q.topic && q.topic.toLowerCase().includes(search));
                return matchDomain && matchSearch;
            });
            currentPage = 0;
            renderQuestions(filteredQuestions);
        }

        function filterByDomain(domain) {
            currentFilter = domain;
            document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.filter-btn').forEach(btn => {
                if (btn.textContent === domain || (domain === 'all' && btn.textContent === 'All')) {
                    btn.classList.add('active');
                }
            });
            filterQuestions();
        }

        function prevPage() {
            if (currentPage > 0) { currentPage--; renderQuestions(filteredQuestions); }
        }

        function nextPage() {
            if ((currentPage + 1) * perPage < filteredQuestions.length) { currentPage++; renderQuestions(filteredQuestions); }
        }

        // Build domain filters
        const domains = [...new Set(allQuestions.map(q => q.domain).filter(d => d))];
        const filterContainer = document.getElementById('domainFilters');
        domains.forEach(domain => {
            const btn = document.createElement('button');
            btn.className = 'filter-btn';
            btn.textContent = domain;
            btn.onclick = () => filterByDomain(domain);
            filterContainer.appendChild(btn);
        });

        renderQuestions(filteredQuestions);
    </script>
</body>
</html>"""
    
    with open('output/all-flashcards.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ Generated flashcards: output/all-flashcards.html")

def main():
    # Read the extracted text file
    input_file = Path("questions/extracted_text.txt")
    
    if not input_file.exists():
        print("❌ File not found: questions/extracted_text.txt")
        print("   Please create this file with the content from your PDF")
        print("   You can copy the text from the PDF into this file")
        print("\n   To extract text from your PDF, you can use:")
        print("   - pdftotext: pdftotext 'Amazon AWS Certified Cloud Practitioner CLF-C02.pdf' questions/extracted_text.txt")
        print("   - Or copy/paste from your PDF reader")
        return
    
    print("📝 Reading extracted text...")
    with open(input_file, 'r', encoding='utf-8') as f:
        text = f.read()
    
    print("📝 Parsing questions...")
    questions = parse_question_blocks(text)
    
    if not questions:
        print("❌ No questions parsed. Please check the format.")
        return
    
    print(f"✅ Parsed {len(questions)} questions")
    
    # Save to JSON
    output_file = Path("questions/all-questions.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({"total": len(questions), "questions": questions}, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Saved to {output_file}")
    
    # Create domain breakdown
    domains = {}
    for q in questions:
        domain = q.get('domain', 'General')
        domains[domain] = domains.get(domain, 0) + 1
    
    print("\n📊 Domain Breakdown:")
    for domain, count in sorted(domains.items(), key=lambda x: x[1], reverse=True):
        print(f"  {domain}: {count} questions")
    
    # Generate HTML flashcards
    generate_flashcards(questions)

if __name__ == "__main__":
    main()
