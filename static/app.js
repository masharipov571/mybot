const tg = window.Telegram.WebApp;
tg.expand();
tg.ready();

const app = {
    user: {
        id: tg.initDataUnsafe?.user?.id || 123456789,
        first_name: tg.initDataUnsafe?.user?.first_name || 'Mehmon',
        username: tg.initDataUnsafe?.user?.username || ''
    },
    currentQuiz: null,
    currentQuestions: [],
    currentQuestionIndex: 0,
    userAnswers: {},
    timerInterval: null,

    init() {
        console.log("App initializing...");
        try {
            const nameEl = document.getElementById('userNameDisplay');
            if (nameEl) nameEl.textContent = this.user.first_name.toUpperCase();
        } catch (e) { console.error("Name display error:", e); }

        // Admin statusini tekshirish, lekin uni kutib o'tirmasdan menyuni ochish
        this.checkAdminStatus().finally(() => {
            this.showView('mainMenu');
        });
    },

    async checkAdminStatus() {
        try {
            const res = await fetch(`/api/admin/check/${this.user.id}`);
            const data = await res.json();
            if (data.is_admin) {
                const adminBtn = document.getElementById('adminBtn');
                if (adminBtn) adminBtn.style.display = 'flex';
            }
        } catch (e) { console.error("Admin status error:", e); }
    },

    showView(viewId) {
        console.log("Showing view:", viewId);
        const views = document.querySelectorAll('.view');
        views.forEach(v => v.classList.remove('active'));

        const targetView = document.getElementById(viewId);
        if (targetView) {
            targetView.classList.add('active');
            window.scrollTo(0, 0);
        } else {
            console.error("View not found:", viewId);
        }
    },

    closeToBot(msg) {
        tg.showAlert(msg);
    },

    copyPrompt() {
        const text = document.getElementById('promptText').innerText;
        navigator.clipboard.writeText(text).then(() => {
            tg.showAlert("Prompt nusxalandi! Uni ChatGPT ga yuboring.");
        });
    },

    async createQuiz() {
        const fileInput = document.getElementById('quizJsonFile');
        const timerInput = document.getElementById('timerInput');
        const titleInput = document.getElementById('quizTitleInput');
        if (!titleInput.value) return tg.showAlert("Iltimos, fan nomini kiriting!");
        if (!fileInput.files[0]) return tg.showAlert("Iltimos, JSON faylni yuklang!");

        tg.showConfirm("Quiz yaratilsinmi?", async (ok) => {
            if (!ok) return;
            const reader = new FileReader();
            reader.onload = async (e) => {
                try {
                    const questions = JSON.parse(e.target.result);
                    const res = await fetch('/api/quiz', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            telegram_id: this.user.id,
                            title: titleInput.value,
                            timer_per_question: parseInt(timerInput.value),
                            questions: questions
                        })
                    });
                    const data = await res.json();
                    tg.showAlert(`Muvaffaqiyatli! Quiz kodi: ${data.code}`);
                    this.showView('mainMenu');
                } catch (err) { tg.showAlert("Fayl formati noto'g'ri!"); }
            };
            reader.readAsText(fileInput.files[0]);
        });
    },

    async joinQuiz() {
        const codeInput = document.getElementById('joinCodeInput');
        const code = codeInput ? codeInput.value : "";
        if (code.length !== 6) return tg.showAlert("6 xonali kod kiriting!");

        try {
            const res = await fetch(`/api/quiz/${code}`);
            if (!res.ok) throw new Error();
            const data = await res.json();
            
            this.currentQuiz = data;
            
            // Chunk selection ko'rsatish
            document.getElementById('chunkSelection').style.display = 'block';
            const chunkList = document.getElementById('chunkList');
            chunkList.innerHTML = '';
            
            const total = data.total_questions;
            const chunkSize = 25;
            for (let i = 0; i < total; i += chunkSize) {
                const start = i + 1;
                const end = Math.min(i + chunkSize, total);
                const card = document.createElement('div');
                card.className = 'menu-card';
                card.style.padding = '12px';
                card.innerHTML = `<span class="menu-title">${start}-${end}</span>`;
                card.onclick = () => this.startQuizChunk(start, end);
                chunkList.appendChild(card);
            }
        } catch (e) { tg.showAlert("Quiz topilmadi!"); }
    },

    async startQuizChunk(start, end) {
        try {
            const res = await fetch(`/api/quiz/${this.currentQuiz.code}?start=${start}&end=${end}`);
            const data = await res.json();
            this.currentQuestions = data.questions;
            this.currentQuestionIndex = 0;
            this.userAnswers = {};
            this.chunkRange = `${start}-${end}`;
            
            document.getElementById('questionsScrollContainer').innerHTML = '';
            this.showView('takingQuizView');
            this.renderNextQuestion();
        } catch (e) { tg.showAlert("Xatolik!"); }
    },

    renderNextQuestion() {
        if (this.currentQuestionIndex >= this.currentQuestions.length) {
            this.finishQuiz();
            return;
        }

        const q = this.currentQuestions[this.currentQuestionIndex];
        const container = document.getElementById('questionsScrollContainer');
        
        const qDiv = document.createElement('div');
        qDiv.className = 'welcome-section';
        qDiv.style.flexDirection = 'column';
        qDiv.style.alignItems = 'flex-start';
        qDiv.style.marginBottom = '20px';
        qDiv.id = `q-block-${this.currentQuestionIndex}`;
        
        qDiv.innerHTML = `
            <p class="q-text" style="font-size:1rem; margin-bottom:16px;">${this.currentQuestionIndex + 1}. ${q.text}</p>
            <div class="options-list" style="width:100%;">
                ${['a', 'b', 'c', 'd'].map((opt, idx) => `
                    <div id="opt-${this.currentQuestionIndex}-${opt}" class="opt-card" 
                         onclick="app.submitAnswer(${this.currentQuestionIndex}, '${opt}')">
                        <div class="opt-label">${String.fromCharCode(65 + idx)}</div>
                        <span>${q['option_' + opt]}</span>
                    </div>
                `).join('')}
            </div>
        `;
        
        container.appendChild(qDiv);
        qDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
        
        document.getElementById('questionCounter').textContent = `Savol: ${this.currentQuestionIndex + 1}/${this.currentQuestions.length}`;
        this.startTimer();
    },

    submitAnswer(qIdx, opt) {
        if (this.userAnswers[qIdx]) return; // Allaqachon javob berilgan
        
        clearInterval(this.timerInterval);
        this.userAnswers[qIdx] = opt;
        const q = this.currentQuestions[qIdx];
        const isCorrect = opt === q.correct_option;
        
        const selectedEl = document.getElementById(`opt-${qIdx}-${opt}`);
        if (isCorrect) {
            selectedEl.classList.add('correct');
        } else {
            selectedEl.classList.add('wrong');
            document.getElementById(`opt-${qIdx}-${q.correct_option}`).classList.add('correct');
        }
        
        this.currentQuestionIndex++;
        setTimeout(() => this.renderNextQuestion(), 600);
    },

    startTimer() {
        clearInterval(this.timerInterval);
        let timeLeft = this.currentQuiz.timer_per_question;
        const timerEl = document.getElementById('questionTimer');
        const update = () => {
            if (timerEl) timerEl.textContent = `00:${timeLeft < 10 ? '0' : ''}${timeLeft}`;
            if (timeLeft <= 0) {
                clearInterval(this.timerInterval);
                this.submitAnswer(this.currentQuestionIndex, 'none');
            }
            timeLeft--;
        };
        update();
        this.timerInterval = setInterval(update, 1000);
    },

    async finishQuiz() {
        this.showView('quizResultView');
        let correct = 0;
        this.currentQuestions.forEach((q, idx) => {
            if (this.userAnswers[idx] === q.correct_option.toLowerCase()) correct++;
        });
        const perc = Math.round((correct / this.currentQuestions.length) * 100);
        document.getElementById('finalScoreDisplay').innerHTML = `
            <div>${perc}%</div>
            <button class="btn-secondary" style="margin-top:20px; width:100%;" onclick="app.startQuizChunk(${this.chunkRange.split('-')[0]}, ${this.chunkRange.split('-')[1]})">Qayta yechish 🔄</button>
        `;

        try {
            await fetch('/api/result', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    telegram_id: this.user.id,
                    quiz_code: this.currentQuiz.code,
                    chunk_range: this.chunkRange,
                    correct_count: correct,
                    incorrect_count: this.currentQuestions.length - correct
                })
            });
        } catch (e) { }
    },

    async loadResults() {
        const container = document.getElementById('resultsContainer');
        container.innerHTML = '<p style="text-align:center;">Yuklanmoqda...</p>';
        try {
            const res = await fetch(`/api/results/${this.user.id}`);
            const data = await res.json();

            let tCorrect = 0, tWrong = 0, tTotalPerc = 0;
            data.forEach(r => {
                tCorrect += r.correct_count;
                tWrong += r.incorrect_count;
                tTotalPerc += (r.correct_count / (r.correct_count + r.incorrect_count)) * 100;
            });

            const avg = data.length > 0 ? Math.round(tTotalPerc / data.length) : 0;
            document.getElementById('stTotal').textContent = data.length;
            document.getElementById('stCorrect').textContent = tCorrect;
            document.getElementById('stWrong').textContent = tWrong;

            const circle = document.getElementById('avgCircle');
            if (circle) {
                circle.style.setProperty('--p', `${avg}%`);
                circle.setAttribute('data-text', `${avg}%`);
            }
            document.getElementById('avgText').textContent = avg >= 80 ? "A'lo" : (avg >= 60 ? "Yaxshi" : "Past");

            container.innerHTML = data.map(r => {
                const p = Math.round((r.correct_count / (r.correct_count + r.incorrect_count)) * 100);
                return `
                    <div class="history-item">
                        <div class="h-icon">📝</div>
                        <div class="h-content">
                            <div class="h-name">Quiz #${r.quiz_code}</div>
                            <div class="h-date">${new Date(r.date).toLocaleDateString()}</div>
                        </div>
                        <div class="h-score-wrap">
                            <span class="h-perc" style="color:${p >= 60 ? 'var(--success)' : 'var(--danger)'}; background:${p >= 60 ? '#f0fdf4' : '#fef2f2'};">${p}%</span>
                            <div class="h-total">${r.correct_count}/${r.correct_count + r.incorrect_count}</div>
                        </div>
                    </div>
                `;
            }).join('');
        } catch (e) { container.innerHTML = 'Xatolik.'; }
    },

    async verifyAdmin() {
        const pass = document.getElementById('adminPass').value;
        try {
            const res = await fetch(`/api/admin/check/${this.user.id}?password=${pass}`);
            const data = await res.json();
            if (data.is_admin) {
                document.getElementById('adminLogin').style.display = 'none';
                document.getElementById('adminContent').style.display = 'block';
                this.loadAdminPanel();
            } else {
                tg.showAlert("Parol noto'g'ri!");
            }
        } catch (e) { tg.showAlert("Xatolik!"); }
    },

    async loadAdminPanel() {
        const container = document.getElementById('adminDataContainer');
        container.innerHTML = '<p style="text-align:center;">Yuklanmoqda...</p>';
        try {
            const res = await fetch(`/api/admin/quizzes?telegram_id=${this.user.id}`);
            const data = await res.json();
            container.innerHTML = data.map(q => `
                <div class="welcome-section" style="flex-direction:column; align-items:flex-start; margin-bottom:12px; padding:16px;">
                    <div style="display:flex; justify-content:space-between; width:100%;">
                        <strong style="color:var(--primary);">#${q.code} - ${q.title}</strong>
                        <button onclick="app.deleteQuiz('${q.code}')" style="background:none; border:none; color:var(--danger); font-weight:800;">X</button>
                    </div>
                    <div style="font-size:0.8rem; color:var(--text-dim); margin-top:4px;">Yaratuvchi: ${q.creator_name} | Savollar: ${q.total_questions} ta</div>
                    <div style="margin-top:10px; width:100%; border-top:1px solid #eee; padding-top:10px;">
                        ${q.participants.map(p => `
                            <div style="font-size:0.75rem; margin-bottom:4px;">👤 ${p.first_name}: ${p.correct}/${p.correct + p.incorrect} (${p.chunk_range})</div>
                        `).join('')}
                    </div>
                </div>
            `).join('');
        } catch (e) { container.innerHTML = 'Xatolik.'; }
    },

    async loadAdminUsers() {
        const container = document.getElementById('adminDataContainer');
        container.innerHTML = '<p style="text-align:center;">Yuklanmoqda...</p>';
        try {
            const res = await fetch(`/api/admin/users?telegram_id=${this.user.id}`);
            const data = await res.json();
            container.innerHTML = `
                <table style="width:100%; font-size:0.8rem; border-collapse:collapse;">
                    <tr style="background:#f8fafc;">
                        <th style="padding:8px; border:1px solid #eee;">Ism</th>
                        <th style="padding:8px; border:1px solid #eee;">ID</th>
                    </tr>
                    ${data.map(u => `
                        <tr>
                            <td style="padding:8px; border:1px solid #eee;">${u.first_name} ${u.username ? '@'+u.username : ''}</td>
                            <td style="padding:8px; border:1px solid #eee;">${u.telegram_id}</td>
                        </tr>
                    `).join('')}
                </table>
            `;
        } catch (e) { container.innerHTML = 'Xatolik.'; }
    },

    async deleteQuiz(code) {
        if (!confirm("O'chirilsinmi?")) return;
        try {
            await fetch(`/api/admin/quiz/${code}?telegram_id=${this.user.id}`, { method: 'DELETE' });
            this.loadAdminPanel();
        } catch (e) { }
    },

    async loadQuizRooms() {
        const container = document.getElementById('quizRoomsContainer');
        container.innerHTML = '<p style="text-align:center;">Yuklanmoqda...</p>';
        try {
            const res = await fetch('/api/public/quizzes');
            const data = await res.json();
            if (data.length === 0) {
                container.innerHTML = '<p style="text-align:center; color:var(--text-dim);">Hozircha ochiq testlar yo\'q.</p>';
                return;
            }
            container.innerHTML = data.map(q => `
                <div class="history-item" onclick="app.joinQuizByCode('${q.code}')" style="cursor:pointer; transition: transform 0.2s;">
                    <div class="h-icon" style="background:#e0e7ff; color:#4338ca;">🔑</div>
                    <div class="h-content">
                        <div class="h-name">${q.title}</div>
                        <div class="h-date">KOD: ${q.code} • ${q.total_questions} savol</div>
                    </div>
                    <div class="h-score-wrap">
                        <span class="h-perc" style="background:#6366f1; color:white; padding:4px 12px; border-radius:20px;">KIRISH</span>
                    </div>
                </div>
            `).join('');
        } catch (e) { container.innerHTML = 'Xatolik yuz berdi.'; }
    },

    joinQuizByCode(code) {
        document.getElementById('joinCodeInput').value = code;
        this.joinQuiz();
    }
};

window.onload = () => app.init();
