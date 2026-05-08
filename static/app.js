// ─── Telegram WebApp ────────────────────────────────────────────────────────
const tg = window.Telegram.WebApp;
tg.expand();
tg.ready();

// ─── App obyekti ────────────────────────────────────────────────────────────
const app = {
    // Foydalanuvchi ma'lumotlari
    user: {
        id:         tg.initDataUnsafe?.user?.id         || 123456789,
        first_name: tg.initDataUnsafe?.user?.first_name || 'Mehmon',
        username:   tg.initDataUnsafe?.user?.username   || ''
    },

    // Quiz holati
    currentQuiz:           null,
    currentQuestions:      [],
    currentQuestionIndex:  0,
    userAnswers:           {},
    timerInterval:         null,
    adminAuthed:           false,  // Admin kodini bir marta kiritsa yetarli
    currentAdminTab:       'quizzes',

    // ─── Ishga tushirish ──────────────────────────────────────────────────
    init() {
        // Ismni ko'rsatish
        const nameEl = document.getElementById('userNameDisplay');
        if (nameEl) nameEl.textContent = this.user.first_name.toUpperCase();

        // Avatar harfini qo'yish
        const avatarEl = document.getElementById('userAvatar');
        if (avatarEl) avatarEl.textContent = (this.user.first_name[0] || 'U').toUpperCase();

        // Admin statusini tekshirish (dashboard ochiladi admin natijasini kutmasdan)
        this.showView('mainMenu');
        this.checkAdminStatus();
        this.loadQuickStats();
    },

    // ─── Admin tekshiruvi ────────────────────────────────────────────────
    async checkAdminStatus() {
        try {
            const res  = await fetch(`/api/admin/check/${this.user.id}`);
            const data = await res.json();
            if (data.is_admin) {
                const btn = document.getElementById('adminBtn');
                if (btn) btn.style.display = 'flex';
            }
        } catch (e) {
            console.warn('Admin check failed:', e);
        }
    },

    // ─── Tezkor statistika ───────────────────────────────────────────────
    async loadQuickStats() {
        try {
            const res  = await fetch(`/api/results/${this.user.id}`);
            const data = await res.json();
            if (!data || data.length === 0) return;

            let total = 0;
            data.forEach(r => {
                const sum = r.correct_count + r.incorrect_count;
                if (sum > 0) total += (r.correct_count / sum) * 100;
            });
            const avg = Math.round(total / data.length);

            const statsBar = document.getElementById('quickStats');
            if (statsBar) {
                document.getElementById('qsTotalTests').textContent = data.length;
                document.getElementById('qsAvgScore').textContent   = avg + '%';
                statsBar.style.display = 'flex';
            }
        } catch (e) {}
    },

    // ─── View almashtirish ───────────────────────────────────────────────
    showView(viewId) {
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        const el = document.getElementById(viewId);
        if (el) {
            el.classList.add('active');
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    },

    // ─── Bot ga qaytish bildiruvi ────────────────────────────────────────
    closeToBot(msg) {
        tg.showAlert(msg);
    },

    // ─── Prompt nusxalash ────────────────────────────────────────────────
    copyPrompt() {
        const text = document.getElementById('promptText')?.innerText || '';
        navigator.clipboard.writeText(text).then(() => {
            tg.showAlert('✅ Prompt nusxalandi!\n\nUni ChatGPT ga yuboring va JSON faylni yuklab oling.');
            const btn = document.getElementById('copyPromptBtn');
            if (btn) { btn.textContent = '✅ Nusxalandi!'; setTimeout(() => btn.textContent = '📋 Promptni Nusxalash', 2000); }
        }).catch(() => {
            tg.showAlert('Nusxalash xatoligi. Qo\'lda nusxalang.');
        });
    },

    // ─── Fayl tanlash ───────────────────────────────────────────────────
    handleFileSelect(input) {
        const area = document.getElementById('fileUploadArea');
        const textEl = document.getElementById('fileUploadText');
        if (input.files[0]) {
            if (textEl) textEl.textContent = '✅ ' + input.files[0].name;
            if (area)  area.style.borderColor = 'var(--success)';
        }
    },

    // ─── Kod input ──────────────────────────────────────────────────────
    handleCodeInput(input) {
        input.value = input.value.replace(/\D/g, '').slice(0, 6);
    },

    // ─── Quiz yaratish ───────────────────────────────────────────────────
    async createQuiz() {
        const fileInput  = document.getElementById('quizJsonFile');
        const timerInput = document.getElementById('timerInput');

        if (!fileInput.files[0]) {
            return tg.showAlert('⚠️ Iltimos, JSON faylni yuklang!');
        }

        tg.showConfirm('Quiz yaratilsinmi?', async (ok) => {
            if (!ok) return;

            const btn = document.getElementById('createQuizBtn');
            if (btn) { btn.textContent = '⏳ Yuklanmoqda...'; btn.disabled = true; }

            const reader = new FileReader();
            reader.onload = async (e) => {
                try {
                    const questions = JSON.parse(e.target.result);
                    if (!Array.isArray(questions) || questions.length === 0) {
                        throw new Error('Noto\'g\'ri format');
                    }

                    const res = await fetch('/api/quiz', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            telegram_id:        this.user.id,
                            timer_per_question: parseInt(timerInput.value) || 30,
                            questions:          questions
                        })
                    });

                    if (!res.ok) throw new Error('Server xatoligi');
                    const data = await res.json();
                    
                    // Natijani ko'rsatish
                    const codeDisplay = document.getElementById('displayQuizCode');
                    if (codeDisplay) codeDisplay.textContent = data.code;
                    this.showView('quizCreatedView');

                } catch (err) {
                    tg.showAlert('❌ ' + (err.message === 'Noto\'g\'ri format'
                        ? 'JSON fayl formati noto\'g\'ri!\nChatGPT dan olingan faylni tekshiring.'
                        : 'Xatolik yuz berdi. Qayta urinib ko\'ring.'));
                } finally {
                    if (btn) { btn.textContent = '✨ Quiz Yaratish'; btn.disabled = false; }
                }
            };
            reader.readAsText(fileInput.files[0]);
        });
    },

    // ─── Quizga qo'shilish ────────────────────────────────────────────────
    async joinQuiz() {
        const codeEl = document.getElementById('joinCodeInput');
        const code   = codeEl?.value.trim() || '';

        if (code.length !== 6) {
            return tg.showAlert('⚠️ 6 xonali quiz kodini kiriting!');
        }

        const btn = document.getElementById('joinQuizBtn');
        if (btn) { btn.textContent = '⏳ Yuklanmoqda...'; btn.disabled = true; }

        try {
            const res = await fetch(`/api/quiz/${code}`);
            if (!res.ok) throw new Error('Not found');

            const data = await res.json();
            if (!data.questions || data.questions.length === 0) {
                throw new Error('Empty quiz');
            }

            this.currentQuiz          = data;
            this.allQuestions         = data.questions; 
            this.showChunks(); 

        } catch (e) {
            tg.showAlert(`❌ Quiz topilmadi!\n\nKodni tekshiring: ${code}`);
        } finally {
            if (btn) { btn.textContent = '🚀 Boshlash'; btn.disabled = false; }
        }
    },

    // ─── Savolni ko'rsatish ───────────────────────────────────────────────
    renderQuestion() {
        const total = this.currentQuestions.length;
        if (this.currentQuestionIndex >= total) {
            this.finishQuiz();
            return;
        }

        const q   = this.currentQuestions[this.currentQuestionIndex];
        const idx = this.currentQuestionIndex;

        // Header
        document.getElementById('questionCounter').textContent =
            `${idx + 1} / ${total}`;
        document.getElementById('qProgressBar').style.width =
            `${((idx + 1) / total) * 100}%`;

        // Savolni render qilish
        const container = document.getElementById('questionsContainer');
        container.innerHTML = `
            <div class="q-text">${idx + 1}. ${q.text}</div>
            <div class="options-list">
                ${['a', 'b', 'c', 'd'].map((opt, i) => `
                    <div class="opt-card ${this.userAnswers[idx] === opt ? 'selected' : ''}"
                         id="opt_${opt}"
                         onclick="app.selectOption('${opt}')">
                        <div class="opt-label">${String.fromCharCode(65 + i)}</div>
                        <span>${q['option_' + opt]}</span>
                    </div>
                `).join('')}
            </div>
        `;

        this.startTimer();
    },

    // ─── Taymer ───────────────────────────────────────────────────────────
    startTimer() {
        clearInterval(this.timerInterval);
        let timeLeft = this.currentQuiz?.timer_per_question || 30;
        const el     = document.getElementById('questionTimer');

        const tick = () => {
            if (el) el.textContent = `00:${timeLeft < 10 ? '0' : ''}${timeLeft}`;
            if (timeLeft <= 0) {
                clearInterval(this.timerInterval);
                this.nextQuestion();
                return;
            }
            timeLeft--;
        };
        tick();
        this.timerInterval = setInterval(tick, 1000);
    },

    // ─── Javob tanlash ────────────────────────────────────────────────────
    selectOption(opt) {
        if (this.feedbackActive) return;
        this.feedbackActive = true;
        
        clearInterval(this.timerInterval);
        
        const idx = this.currentQuestionIndex;
        this.userAnswers[idx] = opt;
        const q = this.currentQuestions[idx];
        const correctOpt = q.correct_option.toLowerCase();

        // Barcha variantlarni o'chirish va ranglarni berish
        document.querySelectorAll('.opt-card').forEach(el => {
            el.classList.add('disabled');
            const elOpt = el.id.replace('opt_', '');
            
            if (elOpt === correctOpt) {
                el.classList.add('correct');
            } else if (elOpt === opt) {
                el.classList.add('wrong-selected');
            } else {
                el.classList.add('wrong');
            }
        });

        // 0.8 soniya kutib keyingiga o'tish (tezkorlik uchun)
        setTimeout(() => {
            this.feedbackActive = false;
            this.nextQuestion();
        }, 800);
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

    // ─── Testni yakunlash ────────────────────────────────────────────────
    async finishQuiz() {
        clearInterval(this.timerInterval);

        let correct = 0;
        this.currentQuestions.forEach((q, idx) => {
            if (this.userAnswers[idx] === q.correct_option.toLowerCase()) correct++;
        });

        const total  = this.currentQuestions.length;
        const wrong  = total - correct;
        const perc   = Math.round((correct / total) * 100);
        const label  = perc >= 90 ? "🏆 A'lo!" : perc >= 75 ? "✅ Yaxshi!" : perc >= 60 ? "📘 Qoniqarli" : "📖 Ko'proq o'qing";

        // Natija ko'rsatish
        document.getElementById('finalScoreDisplay').textContent = `${perc}%`;
        document.getElementById('finalScoreLabel').textContent   = label;
        document.getElementById('resultDetails').innerHTML = `
            <div style="display:flex; gap:16px; justify-content:center; padding:8px 0;">
                <div style="text-align:center;">
                    <div style="font-size:1.5rem; font-weight:800; color:var(--success);">${correct}</div>
                    <div style="font-size:0.7rem; color:var(--text-dim);">To'g'ri</div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:1.5rem; font-weight:800; color:var(--danger);">${wrong}</div>
                    <div style="font-size:0.7rem; color:var(--text-dim);">Noto'g'ri</div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:1.5rem; font-weight:800; color:var(--text);">${total}</div>
                    <div style="font-size:0.7rem; color:var(--text-dim);">Jami</div>
                </div>
            </div>
        `;

        this.showView('quizResultView');

        // Qayta yechish uchun ma'lumotlarni saqlaymiz
        this.lastChunkInfo = { start: this.currentChunkStart, end: this.currentChunkEnd };

        // Natijani bazaga saqlash
        try {
            const rangeStr = `${this.currentChunkStart + 1}-${Math.min(this.currentChunkEnd, this.allQuestions.length)}`;
            await fetch('/api/result', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({
                    telegram_id:     this.user.id,
                    quiz_code:       this.currentQuiz.code,
                    chunk_range:     rangeStr,
                    correct_count:   correct,
                    incorrect_count: wrong
                })
            });
        } catch (e) {
            console.warn('Result save failed:', e);
        }
    },

    // ─── Bloklarni ko'rsatish ──────────────────────────────────────────────
    showChunks() {
        const total = this.allQuestions.length;
        const chunkSize = 25;
        const container = document.getElementById('chunksContainer');
        container.innerHTML = '';
        
        document.getElementById('chunkQuizTitle').textContent = `Quiz #${this.currentQuiz.code}`;

        for (let i = 0; i < total; i += chunkSize) {
            const start = i;
            const end   = Math.min(i + chunkSize, total);
            const card  = document.createElement('div');
            card.className = 'menu-card';
            card.innerHTML = `
                <div class="card-icon blue">📝</div>
                <div class="card-text">
                    <span class="card-title">${start + 1} - ${end} savollar</span>
                    <span class="card-desc">Ushbu blokni yechish</span>
                </div>
                <span class="card-arrow">›</span>
            `;
            card.onclick = () => this.startChunk(start, end);
            container.appendChild(card);
        }
        this.showView('quizChunksView');
    },

    // ─── Blokni boshlash ──────────────────────────────────────────────────
    startChunk(start, end) {
        this.currentChunkStart     = start;
        this.currentChunkEnd       = end;
        
        // Savollardan nusxa olamiz (asl holatiga tegmaslik uchun)
        this.currentQuestions = this.allQuestions.slice(start, end).map(q => {
            const newQ = { ...q };
            const options = [
                { text: q.option_a, key: 'a' },
                { text: q.option_b, key: 'b' },
                { text: q.option_c, key: 'c' },
                { text: q.option_d, key: 'd' }
            ];
            
            // To'g'ri javob matnini saqlab qolamiz
            const correctText = q['option_' + q.correct_option.toLowerCase()];

            // Variantlarni aralashtiramiz (Fisher-Yates shuffle)
            for (let i = options.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                [options[i], options[j]] = [options[j], options[i]];
            }

            // Yangi tartibni savolga yuklaymiz
            newQ.option_a = options[0].text;
            newQ.option_b = options[1].text;
            newQ.option_c = options[2].text;
            newQ.option_d = options[3].text;

            // To'g'ri javobning yangi kalitini aniqlaymiz
            const newKeys = ['a', 'b', 'c', 'd'];
            const newCorrectIdx = options.findIndex(o => o.text === correctText);
            newQ.correct_option = newKeys[newCorrectIdx];

            return newQ;
        });

        this.currentQuestionIndex  = 0;
        this.userAnswers           = {};
        
        this.showView('takingQuizView');
        this.renderQuestion();
    },

    // ─── Qayta yechish ────────────────────────────────────────────────────
    retryQuiz() {
        if (this.lastChunkInfo) {
            this.startChunk(this.lastChunkInfo.start, this.lastChunkInfo.end);
        } else {
            this.showView('mainMenu');
        }
    },

    // ─── Natijalar tarixi ────────────────────────────────────────────────
    async loadResults() {
        const container = document.getElementById('resultsContainer');
        container.innerHTML = '<p class="empty-hint">Yuklanmoqda...</p>';

        try {
            const res  = await fetch(`/api/results/${this.user.id}`);
            const data = await res.json();

            if (!data || data.length === 0) {
                container.innerHTML = '<p class="empty-hint">📭 Hozircha natija yo\'q.\nBiror quizni ishlang!</p>';
                return;
            }

            // Statistika
            let tCorrect = 0, tWrong = 0, totalPerc = 0;
            data.forEach(r => {
                tCorrect += r.correct_count;
                tWrong   += r.incorrect_count;
                const sum = r.correct_count + r.incorrect_count;
                if (sum > 0) totalPerc += (r.correct_count / sum) * 100;
            });
            const avg = data.length > 0 ? Math.round(totalPerc / data.length) : 0;

            document.getElementById('stTotal').textContent   = data.length;
            document.getElementById('stCorrect').textContent = tCorrect;
            document.getElementById('stWrong').textContent   = tWrong;
            document.getElementById('avgText').textContent   =
                avg >= 80 ? "A'lo 🏆" : avg >= 60 ? "Yaxshi ✅" : "Past 📖";

            // Circular progress
            const circle = document.getElementById('avgCircle');
            if (circle) {
                const deg = Math.round((avg / 100) * 360);
                circle.style.setProperty('--progress', `${deg}deg`);
                circle.setAttribute('data-text', `${avg}%`);
            }

            // Tarix ro'yxati
            container.innerHTML = data.map(r => {
                const sum  = r.correct_count + r.incorrect_count;
                const p    = sum > 0 ? Math.round((r.correct_count / sum) * 100) : 0;
                const good = p >= 60;
                const date = r.date ? new Date(r.date).toLocaleDateString('uz-UZ') : '—';
                return `
                    <div class="history-item">
                        <div class="h-icon">📝</div>
                        <div class="h-content">
                            <div class="h-name">Quiz #${r.quiz_code}</div>
                            <div class="h-date">${date} ${r.chunk_range ? '· ' + r.chunk_range : ''}</div>
                        </div>
                        <div class="h-right">
                            <span class="h-perc" style="color:${good ? 'var(--success)' : 'var(--danger)'}; background:${good ? 'var(--success-light)' : 'var(--danger-light)'};">${p}%</span>
                            <div class="h-detail">${r.correct_count}/${sum}</div>
                        </div>
                    </div>
                `;
            }).join('');
        } catch (e) {
            container.innerHTML = '<p class="empty-hint">❌ Xatolik yuz berdi.</p>';
        }
    },

    // ─── Admin autentifikatsiya ──────────────────────────────────────────
    showAdminAuth() {
        if (this.adminAuthed) {
            this.showView('adminView');
            this.loadAdminPanel('quizzes');
            return;
        }
        const input = document.getElementById('adminCodeInput');
        const err   = document.getElementById('adminAuthError');
        if (input) input.value = '';
        if (err)   err.style.display = 'none';
        this.showView('adminAuthView');
    },

    handleAdminCode(input) {
        if (input.value.length === 4) {
            if (input.value === '1213') {
                this.adminAuthed = true;
                this.showView('adminView');
                this.loadAdminPanel('quizzes');
            } else {
                const err = document.getElementById('adminAuthError');
                if (err) err.style.display = 'block';
                input.value = '';
                setTimeout(() => { if (err) err.style.display = 'none'; }, 2000);
            }
        }
    },

    // ─── Admin panel tab ─────────────────────────────────────────────────
    switchAdminTab(tab) {
        this.currentAdminTab = tab;
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        
        let tabId = 'tabQuizzes';
        if (tab === 'results') tabId = 'tabResults';
        if (tab === 'users')   tabId = 'tabUsers';
        
        const tabEl = document.getElementById(tabId);
        if (tabEl) tabEl.classList.add('active');
        this.loadAdminPanel(tab);
    },

    // ─── Admin panel yuklanishi ───────────────────────────────────────────
    async loadAdminPanel(tab = 'quizzes') {
        const container = document.getElementById('adminContainer');
        container.innerHTML = '<p class="empty-hint">Yuklanmoqda...</p>';

        try {
            if (tab === 'quizzes') {
                const res  = await fetch(`/api/admin/quizzes?telegram_id=${this.user.id}`);
                if (!res.ok) throw new Error('Forbidden');
                const data = await res.json();

                if (data.length === 0) {
                    container.innerHTML = '<p class="empty-hint">📭 Hozircha quiz yo\'q.</p>';
                    return;
                }

                container.innerHTML = data.map(q => `
                    <div class="admin-quiz-card">
                        <div class="aq-header">
                            <span class="aq-code">#${q.code}</span>
                            <button class="aq-delete" onclick="app.deleteQuiz('${q.code}')">O'CHIRISH</button>
                        </div>
                        <div class="aq-meta">
                            Yaratuvchi: <b>${q.creator_name}</b>
                            ${q.creator_username ? `(@${q.creator_username})` : ''} ·
                            ${q.total_questions} ta savol ·
                            ${q.participants_count} ishtirokchi ·
                            ${q.created_at}
                        </div>
                        ${q.participants.length > 0 ? `
                        <div class="aq-participants">
                            ${q.participants.map(p => `
                                <div class="aq-p-item">
                                    <span>${p.first_name}${p.username ? ' (@' + p.username + ')' : ''}</span>
                                    <span class="aq-p-score" style="color:${p.percent >= 60 ? 'var(--success)' : 'var(--danger)'}">
                                        ${p.percent}% (${p.correct}/${p.correct + p.incorrect})
                                    </span>
                                </div>
                            `).join('')}
                        </div>` : ''}
                    </div>
                `).join('');

            } else if (tab === 'results') {
                // Test ishlaganlar (Statistika)
                const res  = await fetch(`/api/admin/users?telegram_id=${this.user.id}`);
                if (!res.ok) throw new Error('Forbidden');
                const data = await res.json();
                
                const activeUsers = data.filter(u => u.results_count > 0);
                if (activeUsers.length === 0) {
                    container.innerHTML = '<p class="empty-hint">📭 Hali hech kim test ishlamadi.</p>';
                    return;
                }

                container.innerHTML = activeUsers.map(u => `
                    <div class="admin-user-card">
                        <div class="au-avatar" style="background:var(--success-light); color:var(--success)">${(u.first_name[0] || 'U').toUpperCase()}</div>
                        <div class="au-info">
                            <div class="au-name">${u.first_name}</div>
                            <div class="au-un">${u.username ? '@' + u.username : 'ID: ' + u.telegram_id}</div>
                        </div>
                        <div class="au-count">${u.results_count} ta test</div>
                    </div>
                `).join('');

            } else {
                // Barcha foydalanuvchilar (Start bosganlar)
                const res  = await fetch(`/api/admin/users?telegram_id=${this.user.id}`);
                if (!res.ok) throw new Error('Forbidden');
                const data = await res.json();

                container.innerHTML = `
                    <div style="padding:10px; font-size:0.8rem; color:var(--text-dim);">Jami foydalanuvchilar: ${data.length} ta</div>
                    ${data.map(u => `
                        <div class="admin-user-card">
                            <div class="au-avatar">${(u.first_name[0] || 'U').toUpperCase()}</div>
                            <div class="au-info">
                                <div class="au-name">${u.first_name}</div>
                                <div class="au-un">${u.username ? '@' + u.username : 'ID: ' + u.telegram_id}</div>
                            </div>
                        </div>
                    `).join('')}
                `;
            }
        } catch (e) {
            container.innerHTML = '<p class="empty-hint">❌ Ruxsat yo\'q yoki xatolik.</p>';
        }
    },

    // ─── Quiz o'chirish ───────────────────────────────────────────────────
    deleteQuiz(code) {
        tg.showConfirm(`#${code} quizini o'chirishni tasdiqlaysizmi?`, async (ok) => {
            if (!ok) return;
            try {
                const res = await fetch(`/api/admin/quiz/${code}?telegram_id=${this.user.id}`, {
                    method: 'DELETE'
                });
                if (!res.ok) throw new Error();
                this.loadAdminPanel(this.currentAdminTab);
            } catch (e) {
                tg.showAlert('❌ O\'chirishda xatolik!');
            }
        });
    },

    // ─── Kodni nusxalash ──────────────────────────────────────────────────
    copyQuizCode() {
        const code = document.getElementById('displayQuizCode')?.textContent || '';
        if (code) {
            navigator.clipboard.writeText(code).then(() => {
                tg.showAlert(`📋 Kod nusxalandi: ${code}`);
            }).catch(() => {
                // Clipboard API ishlamasa (ba'zi brauzerlarda)
                tg.showAlert(`Kodni qo'lda nusxalang: ${code}`);
            });
        }
    }
};

// ─── Ishga tushirish ────────────────────────────────────────────────────────
window.addEventListener('load', () => app.init());
