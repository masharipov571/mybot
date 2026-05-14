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
            this.currentQuestions = data.questions;
            this.currentQuestionIndex = 0;
            this.userAnswers = {};
            this.showView('takingQuizView');
            this.renderQuestion();
        } catch (e) { tg.showAlert("Quiz topilmadi!"); }
    },

    renderQuestion() {
        const total = this.currentQuestions.length;
        if (this.currentQuestionIndex >= total) {
            this.finishQuiz();
            return;
        }

        const q = this.currentQuestions[this.currentQuestionIndex];
        document.getElementById('questionCounter').textContent = `Savol: ${this.currentQuestionIndex + 1}/${total}`;
        document.getElementById('qProgressBar').style.width = `${((this.currentQuestionIndex + 1) / total) * 100}%`;

        const container = document.getElementById('questionsContainer');
        container.innerHTML = `
            <p class="q-text">${q.text}</p>
            <div class="options-list">
                ${['a', 'b', 'c', 'd'].map((opt, idx) => `
                    <div class="opt-card ${this.userAnswers[this.currentQuestionIndex] === opt ? 'selected' : ''}" 
                         onclick="app.selectOption('${opt}')">
                        <div class="opt-label">${String.fromCharCode(65 + idx)}</div>
                        <span>${q['option_' + opt]}</span>
                    </div>
                `).join('')}
            </div>
        `;
        this.startTimer();
    },

    startTimer() {
        clearInterval(this.timerInterval);
        let timeLeft = this.currentQuiz.timer_per_question;
        const timerEl = document.getElementById('questionTimer');
        const update = () => {
            if (timerEl) timerEl.textContent = `00:${timeLeft < 10 ? '0' : ''}${timeLeft}`;
            if (timeLeft <= 0) {
                clearInterval(this.timerInterval);
                this.nextQuestion();
            }
            timeLeft--;
        };
        update();
        this.timerInterval = setInterval(update, 1000);
    },

    selectOption(opt) {
        this.userAnswers[this.currentQuestionIndex] = opt;
        this.renderQuestion();
        setTimeout(() => this.nextQuestion(), 200);
    },

    nextQuestion() {
        clearInterval(this.timerInterval);
        this.currentQuestionIndex++;
        this.renderQuestion();
    },

    prevQuestion() {
        if (this.currentQuestionIndex > 0) {
            clearInterval(this.timerInterval);
            this.currentQuestionIndex--;
            this.renderQuestion();
        }
    },

    async finishQuiz() {
        this.showView('quizResultView');
        let correct = 0;
        this.currentQuestions.forEach((q, idx) => {
            if (this.userAnswers[idx] === q.correct_option.toLowerCase()) correct++;
        });
        const perc = Math.round((correct / this.currentQuestions.length) * 100);
        document.getElementById('finalScoreDisplay').textContent = `${perc}%`;

        try {
            await fetch('/api/result', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    telegram_id: this.user.id,
                    quiz_code: this.currentQuiz.code,
                    chunk_range: "1-" + this.currentQuestions.length,
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

    async loadAdminPanel() {
        const container = document.getElementById('adminContainer');
        container.innerHTML = '<p style="text-align:center;">Yuklanmoqda...</p>';
        try {
            const res = await fetch(`/api/admin/quizzes?telegram_id=${this.user.id}`);
            const data = await res.json();
            container.innerHTML = data.map(q => `
                <div class="welcome-section" style="flex-direction:column; align-items:flex-start; margin-bottom:12px; padding:16px;">
                    <div style="display:flex; justify-content:space-between; width:100%;">
                        <strong style="color:var(--primary);">#${q.code}</strong>
                        <button onclick="app.deleteQuiz('${q.code}')" style="background:none; border:none; color:var(--danger); font-weight:800;">O'CHIRISH</button>
                    </div>
                    <div style="font-size:0.8rem; color:var(--text-dim); margin-top:4px;">Yaratuvchi: ${q.creator_name} | Savollar: ${q.total_questions} ta</div>
                </div>
            `).join('');
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
