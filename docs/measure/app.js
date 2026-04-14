/* ─────────────────────────────────────────────────────────────
 *  NX Section Layer Thickness Analyzer — Web version
 *  Pure client-side app:
 *    - Canvas rendering + pan/zoom
 *    - Scale calibration (2-point click + mm input)
 *    - OpenCV.js Canny edge detection along a user-drawn line
 *    - Measurement table
 *    - SheetJS .xlsx export
 * ───────────────────────────────────────────────────────────── */

(() => {
    'use strict';

    // ─── State ────────────────────────────────────────────────
    const state = {
        image: null,               // HTMLImageElement
        imageName: null,
        mode: 'IDLE',              // IDLE | SET_SCALE | DRAW_MEASURE_LINE
        pendingPoint: null,        // First click while in SCALE/MEASURE mode
        // Scale
        scale: {
            p1: null, p2: null,
            realMm: null,
            mmPerPixel: null,
        },
        // Last measure line
        measureLine: null,         // { p1, p2 }
        // Detected layers
        layers: [],                // [{name, yTop, yBot, thicknessPx, thicknessMm}]
        // View transform (pan/zoom)
        view: {
            scale: 1,
            tx: 0,
            ty: 0,
        },
        selectedRow: -1,
    };

    // ─── DOM refs ─────────────────────────────────────────────
    const dom = {
        canvas: document.getElementById('main-canvas'),
        dropZone: document.getElementById('drop-zone'),
        dropHint: document.getElementById('drop-hint'),
        btnOpenFile: document.getElementById('btn-open-file'),
        fileInput: document.getElementById('file-input'),
        btnScale: document.getElementById('btn-scale'),
        btnMeasure: document.getElementById('btn-measure'),
        btnDelete: document.getElementById('btn-delete'),
        btnClear: document.getElementById('btn-clear'),
        btnExport: document.getElementById('btn-export'),
        tableBody: document.getElementById('table-body'),
        statusScale: document.getElementById('status-scale'),
        statusMode: document.getElementById('status-mode'),
        scaleDialog: document.getElementById('scale-dialog'),
        dialogPixelDistance: document.getElementById('dialog-pixel-distance'),
        dialogMm: document.getElementById('dialog-mm'),
        dialogOk: document.getElementById('dialog-ok'),
        dialogCancel: document.getElementById('dialog-cancel'),
        toast: document.getElementById('toast'),
    };

    const ctx = dom.canvas.getContext('2d');

    // ─── Toast helper ─────────────────────────────────────────
    let toastTimer = null;
    function toast(msg, ms = 2400) {
        dom.toast.textContent = msg;
        dom.toast.classList.remove('hidden');
        clearTimeout(toastTimer);
        toastTimer = setTimeout(() => dom.toast.classList.add('hidden'), ms);
    }

    // ─── Image loading ────────────────────────────────────────
    function loadImageFromFile(file) {
        if (!file || !file.type.startsWith('image/')) {
            toast('이미지 파일이 아닙니다.');
            return;
        }
        const reader = new FileReader();
        reader.onload = (e) => {
            const img = new Image();
            img.onload = () => {
                state.image = img;
                state.imageName = file.name;
                state.layers = [];
                state.scale = { p1: null, p2: null, realMm: null, mmPerPixel: null };
                state.measureLine = null;
                state.mode = 'IDLE';
                state.pendingPoint = null;
                resetView();
                resizeCanvas();
                render();
                refreshUI();
                dom.dropHint.classList.add('hidden');
                toast(`이미지 로드: ${file.name}`);
            };
            img.onerror = () => toast('이미지 디코드 실패');
            img.src = e.target.result;
        };
        reader.readAsDataURL(file);
    }

    function resetView() {
        if (!state.image) return;
        const cw = dom.canvas.clientWidth;
        const ch = dom.canvas.clientHeight;
        const iw = state.image.naturalWidth;
        const ih = state.image.naturalHeight;
        const scale = Math.min(cw / iw, ch / ih, 1);
        state.view.scale = scale;
        state.view.tx = (cw - iw * scale) / 2;
        state.view.ty = (ch - ih * scale) / 2;
    }

    // ─── Canvas sizing ────────────────────────────────────────
    function resizeCanvas() {
        const rect = dom.dropZone.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        dom.canvas.width = rect.width * dpr;
        dom.canvas.height = rect.height * dpr;
        dom.canvas.style.width = rect.width + 'px';
        dom.canvas.style.height = rect.height + 'px';
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    // ─── Coordinate conversion ────────────────────────────────
    function canvasToImage(cx, cy) {
        return {
            x: (cx - state.view.tx) / state.view.scale,
            y: (cy - state.view.ty) / state.view.scale,
        };
    }
    function imageToCanvas(ix, iy) {
        return {
            x: ix * state.view.scale + state.view.tx,
            y: iy * state.view.scale + state.view.ty,
        };
    }

    // ─── Rendering ────────────────────────────────────────────
    function render() {
        const w = dom.canvas.clientWidth;
        const h = dom.canvas.clientHeight;
        ctx.save();
        ctx.fillStyle = '#1e293b';
        ctx.fillRect(0, 0, w, h);
        ctx.restore();

        if (!state.image) return;

        // Draw image with current view transform.
        ctx.save();
        ctx.translate(state.view.tx, state.view.ty);
        ctx.scale(state.view.scale, state.view.scale);
        ctx.drawImage(state.image, 0, 0);
        ctx.restore();

        // Overlays (in canvas coords, using view transform).
        drawOverlays();
    }

    function drawOverlays() {
        // Scale line (blue)
        if (state.scale.p1 && state.scale.p2) {
            drawLine(state.scale.p1, state.scale.p2, '#60a5fa', 2);
            drawDot(state.scale.p1, '#60a5fa');
            drawDot(state.scale.p2, '#60a5fa');
        }
        // Pending first point in any mode
        if (state.pendingPoint) {
            drawDot(state.pendingPoint, '#fbbf24');
        }
        // Measurement line (green)
        if (state.measureLine) {
            drawLine(state.measureLine.p1, state.measureLine.p2, '#34d399', 2);
        }
        // Layer boundaries (red ticks)
        if (state.layers.length && state.measureLine) {
            const { p1 } = state.measureLine;
            const boundaries = [];
            for (const layer of state.layers) {
                boundaries.push(layer.yTop);
            }
            boundaries.push(state.layers[state.layers.length - 1].yBot);
            for (let i = 0; i < boundaries.length; i++) {
                const y = boundaries[i];
                const cp = imageToCanvas(p1.x, y);
                ctx.save();
                ctx.strokeStyle = '#ef4444';
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.moveTo(cp.x - 24, cp.y);
                ctx.lineTo(cp.x + 24, cp.y);
                ctx.stroke();
                ctx.fillStyle = '#ef4444';
                ctx.font = '12px -apple-system, sans-serif';
                ctx.fillText(`b${i}`, cp.x + 28, cp.y + 4);
                ctx.restore();
            }
        }
    }

    function drawLine(p1, p2, color, width) {
        const a = imageToCanvas(p1.x, p1.y);
        const b = imageToCanvas(p2.x, p2.y);
        ctx.save();
        ctx.strokeStyle = color;
        ctx.lineWidth = width;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
        ctx.restore();
    }
    function drawDot(p, color) {
        const a = imageToCanvas(p.x, p.y);
        ctx.save();
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(a.x, a.y, 4, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
    }

    // ─── Mode management ──────────────────────────────────────
    function setMode(mode) {
        state.mode = mode;
        state.pendingPoint = null;
        if (mode === 'IDLE') {
            dom.statusMode.textContent = '탐색';
            dom.canvas.classList.remove('mode-crosshair');
        } else if (mode === 'SET_SCALE') {
            dom.statusMode.textContent = '기준선 설정 (두 점 클릭)';
            dom.canvas.classList.add('mode-crosshair');
        } else if (mode === 'DRAW_MEASURE_LINE') {
            dom.statusMode.textContent = '측정선 그리기 (두 점 클릭)';
            dom.canvas.classList.add('mode-crosshair');
        }
        render();
    }

    // ─── UI state refresh ─────────────────────────────────────
    function refreshUI() {
        const hasImage = !!state.image;
        const hasLayers = state.layers.length > 0;
        dom.btnScale.disabled = !hasImage;
        dom.btnMeasure.disabled = !hasImage;
        dom.btnClear.disabled = !hasLayers;
        dom.btnDelete.disabled = !hasLayers || state.selectedRow < 0;
        dom.btnExport.disabled = !hasLayers;
        if (state.scale.mmPerPixel) {
            dom.statusScale.textContent = `${state.scale.mmPerPixel.toFixed(5)} mm/px`;
        } else {
            dom.statusScale.textContent = '미설정';
        }
        renderTable();
    }

    // ─── Click handling ───────────────────────────────────────
    dom.canvas.addEventListener('mousedown', (e) => {
        if (!state.image) return;
        if (e.button !== 0) return;
        const rect = dom.canvas.getBoundingClientRect();
        const cx = e.clientX - rect.left;
        const cy = e.clientY - rect.top;

        if (state.mode === 'IDLE') {
            // Start panning
            panStart(cx, cy);
            return;
        }
        // SET_SCALE or DRAW_MEASURE_LINE — click point capture
        const imgPt = canvasToImage(cx, cy);
        if (!state.pendingPoint) {
            state.pendingPoint = imgPt;
            toast('두 번째 점을 클릭하세요');
            render();
            return;
        }
        const p1 = state.pendingPoint;
        let p2 = imgPt;
        state.pendingPoint = null;

        if (state.mode === 'SET_SCALE') {
            state.scale.p1 = p1;
            state.scale.p2 = p2;
            openScaleDialog(p1, p2);
            setMode('IDLE');
        } else if (state.mode === 'DRAW_MEASURE_LINE') {
            // Snap to vertical unless Shift is held.
            if (!e.shiftKey) {
                p2 = { x: p1.x, y: p2.y };
            }
            state.measureLine = { p1, p2 };
            setMode('IDLE');
            runEdgeDetection();
        }
    });

    // ─── Pan (drag) ───────────────────────────────────────────
    let panning = null;
    function panStart(cx, cy) {
        panning = { cx, cy, tx: state.view.tx, ty: state.view.ty };
        dom.canvas.style.cursor = 'grabbing';
    }
    window.addEventListener('mousemove', (e) => {
        if (!panning) return;
        const rect = dom.canvas.getBoundingClientRect();
        const cx = e.clientX - rect.left;
        const cy = e.clientY - rect.top;
        state.view.tx = panning.tx + (cx - panning.cx);
        state.view.ty = panning.ty + (cy - panning.cy);
        render();
    });
    window.addEventListener('mouseup', () => {
        if (panning) {
            panning = null;
            dom.canvas.style.cursor = '';
        }
    });

    // ─── Zoom (wheel) ─────────────────────────────────────────
    dom.canvas.addEventListener('wheel', (e) => {
        if (!state.image) return;
        e.preventDefault();
        const rect = dom.canvas.getBoundingClientRect();
        const cx = e.clientX - rect.left;
        const cy = e.clientY - rect.top;
        const factor = e.deltaY < 0 ? 1.15 : 1 / 1.15;
        // Zoom towards mouse cursor.
        const imgPt = canvasToImage(cx, cy);
        state.view.scale *= factor;
        state.view.scale = Math.max(0.05, Math.min(20, state.view.scale));
        state.view.tx = cx - imgPt.x * state.view.scale;
        state.view.ty = cy - imgPt.y * state.view.scale;
        render();
    }, { passive: false });

    // ─── Drag & drop ──────────────────────────────────────────
    ['dragenter', 'dragover'].forEach((ev) => {
        dom.dropZone.addEventListener(ev, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dom.dropZone.classList.add('dragover');
        });
    });
    ['dragleave', 'drop'].forEach((ev) => {
        dom.dropZone.addEventListener(ev, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dom.dropZone.classList.remove('dragover');
        });
    });
    dom.dropZone.addEventListener('drop', (e) => {
        const file = e.dataTransfer?.files?.[0];
        if (file) loadImageFromFile(file);
    });

    // ─── File picker ──────────────────────────────────────────
    dom.btnOpenFile.addEventListener('click', () => dom.fileInput.click());
    dom.fileInput.addEventListener('change', (e) => {
        const file = e.target.files?.[0];
        if (file) loadImageFromFile(file);
        dom.fileInput.value = '';
    });

    // ─── Scale dialog ─────────────────────────────────────────
    function openScaleDialog(p1, p2) {
        const dx = p2.x - p1.x;
        const dy = p2.y - p1.y;
        const dist = Math.hypot(dx, dy);
        dom.dialogPixelDistance.textContent = dist.toFixed(2) + ' px';
        dom.dialogMm.value = '10';
        dom.scaleDialog.classList.remove('hidden');
        setTimeout(() => dom.dialogMm.focus(), 50);
        dom.scaleDialog.dataset.pixelDistance = String(dist);
    }
    function closeScaleDialog() {
        dom.scaleDialog.classList.add('hidden');
    }
    dom.dialogCancel.addEventListener('click', () => {
        state.scale.p1 = null;
        state.scale.p2 = null;
        closeScaleDialog();
        render();
    });
    dom.dialogOk.addEventListener('click', () => {
        const dist = parseFloat(dom.scaleDialog.dataset.pixelDistance);
        const mm = parseFloat(dom.dialogMm.value);
        if (!(dist > 0) || !(mm > 0)) {
            toast('올바른 값을 입력하세요');
            return;
        }
        state.scale.realMm = mm;
        state.scale.mmPerPixel = mm / dist;
        closeScaleDialog();
        // Recompute mm column of existing layers.
        for (const layer of state.layers) {
            layer.thicknessMm = layer.thicknessPx * state.scale.mmPerPixel;
        }
        refreshUI();
        render();
        toast(`스케일 보정: ${state.scale.mmPerPixel.toFixed(5)} mm/px`);
    });
    dom.dialogMm.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') dom.dialogOk.click();
        if (e.key === 'Escape') dom.dialogCancel.click();
    });

    // ─── Buttons ──────────────────────────────────────────────
    dom.btnScale.addEventListener('click', () => setMode('SET_SCALE'));
    dom.btnMeasure.addEventListener('click', () => {
        if (!state.scale.mmPerPixel) {
            if (!confirm('기준선이 설정되지 않았습니다. 계속하시겠습니까?\n(mm 값은 0으로 표시됩니다)')) {
                return;
            }
        }
        setMode('DRAW_MEASURE_LINE');
    });
    dom.btnClear.addEventListener('click', () => {
        state.layers = [];
        state.measureLine = null;
        state.selectedRow = -1;
        refreshUI();
        render();
    });
    dom.btnDelete.addEventListener('click', () => {
        if (state.selectedRow < 0) return;
        state.layers.splice(state.selectedRow, 1);
        // Rename sequentially.
        state.layers.forEach((layer, i) => { layer.name = `Layer ${i + 1}`; });
        state.selectedRow = -1;
        refreshUI();
        render();
    });
    dom.btnExport.addEventListener('click', exportXlsx);

    // ─── Edge detection (OpenCV.js port of edge_detector.py) ──
    function runEdgeDetection() {
        if (!window.__cvReady) {
            toast('OpenCV.js 아직 로딩 중...');
            return;
        }
        if (!state.measureLine || !state.image) return;

        const { p1, p2 } = state.measureLine;
        // Build an offscreen canvas with the raw image, read pixels.
        const off = document.createElement('canvas');
        off.width = state.image.naturalWidth;
        off.height = state.image.naturalHeight;
        const offCtx = off.getContext('2d');
        offCtx.drawImage(state.image, 0, 0);

        let src, gray, blurred, edges;
        try {
            src = cv.imread(off);
            gray = new cv.Mat();
            cv.cvtColor(src, gray, cv.COLOR_RGBA2GRAY);
            blurred = new cv.Mat();
            cv.GaussianBlur(gray, blurred, new cv.Size(3, 3), 0);
            // Auto Canny thresholds based on median.
            const data = blurred.data;
            const sorted = Array.from(data).sort((a, b) => a - b);
            const median = sorted[Math.floor(sorted.length / 2)];
            const sigma = 0.33;
            const low = Math.max(0, (1 - sigma) * median);
            const high = Math.min(255, (1 + sigma) * median);
            edges = new cv.Mat();
            cv.Canny(blurred, edges, low, Math.max(low + 1, high));

            // Sample edge values along the line using numpy.linspace-style sampling.
            const w = edges.cols;
            const h = edges.rows;
            const len = Math.max(
                Math.round(Math.max(Math.abs(p2.x - p1.x), Math.abs(p2.y - p1.y))) + 1,
                2
            );
            const hits = [];
            const edgeData = edges.data;
            for (let i = 0; i < len; i++) {
                const t = i / (len - 1);
                const xi = Math.min(w - 1, Math.max(0, Math.round(p1.x + (p2.x - p1.x) * t)));
                const yi = Math.min(h - 1, Math.max(0, Math.round(p1.y + (p2.y - p1.y) * t)));
                if (edgeData[yi * w + xi] > 0) hits.push(i);
            }

            // Merge adjacent hits.
            const mergeGap = 2;
            const groups = [];
            for (const idx of hits) {
                if (groups.length && idx - groups[groups.length - 1][groups[groups.length - 1].length - 1] <= mergeGap) {
                    groups[groups.length - 1].push(idx);
                } else {
                    groups.push([idx]);
                }
            }
            const boundaryTs = groups.map((g) => g.reduce((a, b) => a + b, 0) / g.length);

            if (boundaryTs.length < 2) {
                toast('레이어를 찾지 못했습니다. 측정선 위치를 조정하세요.');
                return;
            }

            // Convert t (along sampled line) back to y image coordinates.
            const total = len - 1;
            const verticalDominant = Math.abs(p2.y - p1.y) >= Math.abs(p2.x - p1.x);
            const tToY = (t) => p1.y + (p2.y - p1.y) * (t / total);

            const minThicknessPx = 2.0;
            const layers = [];
            for (let i = 0; i < boundaryTs.length - 1; i++) {
                const yTop = tToY(boundaryTs[i]);
                const yBot = tToY(boundaryTs[i + 1]);
                let thicknessPx;
                if (verticalDominant) {
                    thicknessPx = Math.abs(yBot - yTop);
                } else {
                    thicknessPx = Math.abs(boundaryTs[i + 1] - boundaryTs[i]);
                }
                if (thicknessPx < minThicknessPx) continue;
                layers.push({
                    name: `Layer ${layers.length + 1}`,
                    yTop,
                    yBot,
                    thicknessPx,
                    thicknessMm: state.scale.mmPerPixel ? thicknessPx * state.scale.mmPerPixel : 0,
                });
            }
            state.layers = layers;
            state.selectedRow = -1;
            refreshUI();
            render();
            toast(`${layers.length}개 레이어 검출`);
        } catch (err) {
            console.error(err);
            toast('검출 실패: ' + err.message);
        } finally {
            if (src) src.delete();
            if (gray) gray.delete();
            if (blurred) blurred.delete();
            if (edges) edges.delete();
        }
    }

    // ─── Table rendering ──────────────────────────────────────
    function renderTable() {
        if (state.layers.length === 0) {
            dom.tableBody.innerHTML = `
                <tr class="empty-row">
                    <td colspan="5">이미지를 불러오고<br>측정선을 그으면 채워집니다</td>
                </tr>`;
            return;
        }
        const rows = state.layers.map((layer, i) => {
            const sel = i === state.selectedRow ? ' class="selected"' : '';
            return `<tr${sel} data-row="${i}">
                <td contenteditable="true">${escapeHtml(layer.name)}</td>
                <td>${layer.yTop.toFixed(1)}</td>
                <td>${layer.yBot.toFixed(1)}</td>
                <td>${layer.thicknessPx.toFixed(1)}</td>
                <td>${layer.thicknessMm.toFixed(3)}</td>
            </tr>`;
        }).join('');
        dom.tableBody.innerHTML = rows;

        // Attach row click / edit handlers.
        dom.tableBody.querySelectorAll('tr').forEach((tr) => {
            const idx = parseInt(tr.dataset.row, 10);
            tr.addEventListener('click', (e) => {
                if (e.target.isContentEditable) return;
                state.selectedRow = idx;
                refreshUI();
            });
            const nameCell = tr.querySelector('td[contenteditable]');
            if (nameCell) {
                nameCell.addEventListener('blur', () => {
                    state.layers[idx].name = nameCell.textContent.trim() || `Layer ${idx + 1}`;
                });
                nameCell.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') { e.preventDefault(); nameCell.blur(); }
                });
            }
        });
    }

    function escapeHtml(s) {
        return String(s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    // ─── Export xlsx ──────────────────────────────────────────
    function exportXlsx() {
        if (state.layers.length === 0) {
            toast('내보낼 데이터가 없습니다');
            return;
        }
        if (typeof XLSX === 'undefined') {
            toast('SheetJS 로딩 중...');
            return;
        }
        const metaRows = [
            ['Image', state.imageName || ''],
            ['mm per pixel', state.scale.mmPerPixel || 'n/a'],
            [],
            ['Layer', 'Top (px)', 'Bottom (px)', 'Thickness (px)', 'Thickness (mm)'],
        ];
        for (const layer of state.layers) {
            metaRows.push([
                layer.name,
                round(layer.yTop, 2),
                round(layer.yBot, 2),
                round(layer.thicknessPx, 2),
                round(layer.thicknessMm, 4),
            ]);
        }
        const ws = XLSX.utils.aoa_to_sheet(metaRows);
        ws['!cols'] = [
            { wch: 18 }, { wch: 12 }, { wch: 12 }, { wch: 15 }, { wch: 15 },
        ];
        const wb = XLSX.utils.book_new();
        const sheetName = (state.imageName || 'Measurement').replace(/\.[^.]+$/, '').slice(0, 31);
        XLSX.utils.book_append_sheet(wb, ws, sheetName);
        const outName = (state.imageName || 'measurements').replace(/\.[^.]+$/, '') + '_measurements.xlsx';
        XLSX.writeFile(wb, outName);
        toast(`저장됨: ${outName}`);
    }
    function round(v, n) {
        const p = Math.pow(10, n);
        return Math.round((v || 0) * p) / p;
    }

    // ─── Resize ───────────────────────────────────────────────
    window.addEventListener('resize', () => {
        resizeCanvas();
        if (state.image) {
            // Keep view centered if image is smaller than canvas.
            render();
        }
    });

    // ─── Init ─────────────────────────────────────────────────
    resizeCanvas();
    render();
    refreshUI();
})();
