# VentureAgent - Güncelleme Raporu (haticenury branch)

Bu rapor, `main` branch'inde arkadaşınızın yaptığı değişikliklerin üzerine, bizim bu oturumda geliştirdiğimiz özellikleri **mimariyi bozmadan** aktarmak (port etmek) üzere diğer AI asistanı (Code Agent) için hazırlanmıştır.

Lütfen bu raporu diğer ajana vererek şunları uygulamasını isteyin.

## 🎯 Yapılan Değişikliklerin Özeti

1. **Markdown Formatlama Sorununun Çözümü:** AI'dan gelen ham markdown (örneğin `### Başlık`, `**kalın**`) çıktısı, sayfalarda `<pre>` etiketiyle düz metin olarak görünüyordu. Bu sorun `marked.js` kütüphanesi ve `.md-output` CSS sınıfı ile çözüldü.
2. **Sohbet (Chat) Arayüzü Markdown Desteği:** Chat arayüzünde asistan cevaplarının da doğru HTML hiyerarşisiyle (liste, kalın yazı vs.) görünmesi sağlandı. (Hem yeni mesajlar hem de geçmiş mesajlar için).
3. **PPTX (PowerPoint) İndirme Özelliği:** Pitch (Sunum) ve Yatırımcı analiz sayfalarına PPTX formatında çıktı alma özelliği eklendi.
4. **PPTX Taşma (Overflow) ve Uzun Metin Çözümü:** PowerPoint dosyasına yazılan metinler uzun olduğunda üst üste biniyordu. Satır uzunluklarını karakter bazında analiz eden dinamik bir `_chunk_bullets_by_height` fonksiyonu yazılarak uzun içeriklerin otomatik olarak yeni slaytlara taşması sağlandı. Kapak sayfasındaki Fikir başlıkları için akıllı kısaltma algoritması eklendi.
5. **Görsel (Image) Üretme Modülünün Kaldırılması:** `idea.html` ve `pitch.html` dosyalarındaki resim oluşturma özellikleri (kullanıcı isteğiyle) arayüzden tamamen temizlendi.
6. **Token Limiti Artırımı:** `idea.py` içindeki analiz token limiti 1200'den 3000'e çıkarılarak detaylı analizlerin yarıda kesilmesi sorunu çözüldü.

---

## 🛠️ Code Agent İçin Adım Adım Entegrasyon Rehberi

> [!IMPORTANT]
> Sayın Code Agent: Lütfen aşağıdaki değişiklikleri projenin mevcut `main` branch'ine entegre et. Flask mimarisini, mevcut route'ları veya diğer veritabanı/session işlemlerini KESİNLİKLE değiştirme. Sadece UI, formatlama ve yeni export işlevlerini ekle.

### 1. Yeni Eklenen Bağımlılık
`requirements.txt` dosyasına ekle:
```
python-pptx==1.0.2
```

### 2. Markdown Rendering Entegrasyonu (Frontend CSS & JS)

**Dosya:** `frontend/templates/base.html`
- `</body>` kapanış etiketinden hemen önce (block scripts kısmının üstüne) marked.js'i ekle:
```html
{# marked.js – lightweight markdown-to-HTML, used by analysis result pages #}
<script src="https://cdn.jsdelivr.net/npm/marked@12/marked.min.js"></script>
```

**Dosya:** `frontend/static/css/style.css`
- `.result pre` tanımlamasının altına (ve `.error`'un üstüne) şu `.md-output` sınıflarını ekle:
```css
/* ── Markdown rendered output ─────────────────────────────────────────── */
.md-output { line-height: 1.75; color: var(--text); }
.md-output h1,
.md-output h2,
.md-output h3 { font-family: var(--font-heading); color: var(--teal-dark); margin: 1.4rem 0 0.4rem; }
.md-output h1 { font-size: 1.25rem; }
.md-output h2 { font-size: 1.1rem; }
.md-output h3 { font-size: 0.97rem; text-transform: uppercase; letter-spacing: 0.06em; }
.md-output p  { margin: 0.55rem 0; }
.md-output ul,
.md-output ol { padding-left: 1.4rem; margin: 0.5rem 0; }
.md-output li { margin: 0.3rem 0; }
.md-output strong { font-weight: 600; color: var(--text); }
.md-output em { color: var(--text-muted); font-style: italic; }
.md-output hr { border: none; border-top: 1px solid var(--line); margin: 1.2rem 0; }
.md-output code { background: var(--surface-strong); border-radius: 4px; padding: 1px 5px; font-size: 0.88em; }
.md-output blockquote { border-left: 3px solid var(--teal); margin: 0.8rem 0; padding: 0.4rem 1rem; color: var(--text-muted); font-style: italic; }
```

### 3. Arayüzlerde Markdown Çıktıları ve Export Butonları (HTML Dosyaları)

**Dosya:** `frontend/templates/idea.html`
- Görsel üretme ile ilgili HTML kodları, scriptler ve varsa ilgili butonları tamamen kaldır.
- `{% if analysis %}` altındaki içeriği (`<pre>{{ analysis }}</pre>`) şu şekilde değiştir:
```html
<div class="result">
    <h2>Analiz Sonucu</h2>
    <div id="analysis-content" class="md-output"></div>
</div>
```
- Dosyanın sonuna script bloğunu ekle:
```html
{% block scripts %}
{% if analysis %}
<script>
    document.getElementById('analysis-content').innerHTML =
        marked.parse({{ analysis | tojson }});
</script>
{% endif %}
{% endblock %}
```

**Dosya:** `frontend/templates/investors.html`
- Analiz sonucunu gösteren bloğu `div#advice-content` yap ve script bloğunu ekle. Ayrıca PPTX Export buton formunu `advice-content` div'inin sonrasına içeriğe ekle.
```html
{% if advice %}
    <div class="result">
        <div id="advice-content" class="md-output"></div>

        {# ── PPTX Export ─────────────────────────────────────────────── #}
        <form method="POST" action="{{ url_for('export.investors_pptx') }}" style="margin-top:20px;">
            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
            <input type="hidden" name="idea" value="{{ idea or '' }}">
            <input type="hidden" name="stage" value="{{ request.form.get('stage', '') }}">
            <input type="hidden" name="advice" value="{{ advice | forceescape }}">
            <button type="submit" class="btn-secondary">
                ⬇ Raporu İndir (.pptx)
            </button>
        </form>
    </div>
{% endif %}
```
*(Script bloğunu `idea.html`'deki gibi advice değişkeni için eklemeyi unutma)*.

**Dosya:** `frontend/templates/pitch.html`
- Görsel oluşturma kısımlarını tamamen kaldır.
- Elevator pitch gösterimini `<div id="elevator-content" class="md-output"></div>` olarak güncelle ve block script bloğunda `marked.parse` scriptini (`elevator` değişkeni için) ekle.
- Slaytlar (`{% if slides %}`) kısmında Listenin altına PPTX Export formu ekle:
```html
            {# ── PPTX Export ─────────────────────────────────────────────── #}
            <form method="POST" action="{{ url_for('export.pitch_pptx') }}" style="margin-top:20px;">
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                <input type="hidden" name="idea" value="{{ submitted_idea if submitted_idea else (active_idea.idea if active_idea else '') }}">
                <input type="hidden" name="slides_json" value="{{ slides | tojson | forceescape }}">
                <button type="submit" class="btn-secondary">
                    ⬇ Sunumu İndir (.pptx)
                </button>
            </form>
```

### 4. Chat Ekranı Formatlaması

**Dosya:** `frontend/templates/chat.html`
- Geçmiş mesajlar döngüsünü güncelle:
```html
<div class="chat-bubble chat-{{ msg.role }}{% if msg.role == 'assistant' %} md-output{% endif %}">{{ msg.content }}</div>
```

**Dosya:** `frontend/static/js/chat.js`
- `appendBubble` fonksiyonunu asistan yanıtları için `innerHTML` ile güncelleyin:
```javascript
function appendBubble(role, content) {
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble chat-${role} md-output`;
    if (role === "assistant" && typeof marked !== "undefined") {
        bubble.innerHTML = marked.parse(content);
    } else {
        bubble.textContent = content;
    }
//...
```
- API'den dönen yanıtı eklerken:
```javascript
if (typeof marked !== "undefined") {
    thinkingBubble.innerHTML = marked.parse(data.reply);
} else {
    thinkingBubble.textContent = data.reply;
}
```
- Sayfa yüklendiğinde eski geçmişi render etmek için kodun en altına ekleyin:
```javascript
// Re-render existing history bubbles (server-side rendered) with markdown
document.querySelectorAll(".chat-assistant").forEach(function(bubble) {
    if (typeof marked !== "undefined" && bubble.dataset.mdRendered !== "1") {
        bubble.classList.add("md-output");
        bubble.innerHTML = marked.parse(bubble.textContent || "");
        bubble.dataset.mdRendered = "1";
    }
});
```

### 5. Backend Route Limit ve Veri İletimi

**Dosya:** `backend/routes/idea.py`
- `analyze_idea` metodundaki `ask_ai` çağrısında `max_tokens` değerini `1200`'den `3000`'e yükseltin. (Analizin yarıda kesilmesini engeller).

**Dosya:** `backend/routes/pitch.py`
- Deck oluşturulduğunda (`pitch_type == "deck"`) dönen `render_template` çağrısına formdaki fikri `submitted_idea=idea` olarak ekleyin (Export formuna veri aktarmak için):
```python
return render_template("pitch.html", elevator=None, slides=slides, active_idea=get_active_idea(), submitted_idea=idea)
```

**Dosya:** `backend/routes/investors.py`
- Hem `try` bloğu içindeki hata durumundaki render'a hem de başarılı durumdaki `render_template` çağrısına `idea=idea` değişkenini geçin (Export formuna veri gitmesi için).
```python
return render_template("investors.html", advice=advice, active_idea=get_active_idea(), idea=idea)
```

### 6. Yeni Eklenen Export Modülü

Bu iki yeni python dosyasını projeye dahil edin:
- `backend/routes/export.py` (PPTX İndirme route'ları, formdan gelen veriyi alır)
- `backend/services/pptx_export.py` (python-pptx ile asıl sunum üretimini yapan algoritma. Dinamik yükseklik ölçümü `_bullet_height` ve taşma kontrolü `_chunk_bullets_by_height` içermelidir). 

**Dosya:** `backend/__init__.py`
- Yeni `export.py` router'ını kaydedin (`from backend.routes.export import export_bp` ve `app.register_blueprint(export_bp, url_prefix="/export")`).

> [!TIP]
> Eğer haticenury branch'inde yer alan `backend/routes/image.py` ve `backend/services/image_gen.py` dosyalarına rastlarsanız, arayüzden görseller kaldırıldığı için bu dosyalara `main` branch'inde ihtiyaç yoktur; entegre etmeniz gerekmez. Sadece PPTX export dosyaları elzemdir.
