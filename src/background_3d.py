"""
MSRA 3D Animated Background & Mobile Surface Architecture
=========================================================
This module provides a robust, battery-efficient 3D animated particle background
(Three.js WebGL network with automated HTML5 Canvas 2D fallback) and guarantees
complete cross-device visibility on desktop and mobile browsers.

ISOLATION GUARANTEE:
All 3D/particle code, canvas resizing, orientation handling, and sidebar reopen
toggle hooks are strictly encapsulated.
"""

import streamlit as st
import streamlit.components.v1 as components

# ==============================================================================
# CONFIGURATION
# ==============================================================================
ENABLE_3D_BACKGROUND = True
BACKGROUND_STYLE = "three"  # Options: "three" (Three.js WebGL + 2D fallback) or "css"

# Pinned Three.js CDN version (r128)
THREE_JS_CDN = "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"


def _inject_surface_transparency():
    """Ensures Streamlit surface containers allow the background effect to show through,
    while keeping the sidebar solid #0a0a0a and positioning the canvas safely behind
    all interactive workspace content.
    """
    st.markdown("""
<style>
/* 1. Base Surfaces: html provides deep black, body & app views are transparent */
html {
    background-color: #000000 !important;
}
html body,
html body div.stApp,
html body div[data-testid="stAppViewContainer"],
html body section[data-testid="stMain"],
html body div[data-testid="stMainBlockContainer"],
html body div.block-container {
    background-color: transparent !important;
    background: transparent !important;
}

/* 2. Main content block stays above background but allows interaction */
html body div[data-testid="stAppViewContainer"] {
    position: relative !important;
    z-index: 1 !important;
}

/* 3. Sidebar stays solid dark #0a0a0a above background */
html body section[data-testid="stSidebar"] {
    background-color: #0a0a0a !important;
    z-index: 100 !important;
}

/* 4. Canvas element fixed behind content */
#msra-3d-canvas {
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    width: 100vw !important;
    height: 100vh !important;
    height: 100dvh !important;
    z-index: 0 !important;
    pointer-events: none !important;
    display: block !important;
    border: none !important;
}

/* 5. Streamlit component wrapper takes zero space in flow */
div[data-testid="stCustomComponentV1"],
div:has(> iframe[data-testid="stCustomComponentV1"]) {
    position: absolute !important;
    top: 0 !important;
    left: 0 !important;
    width: 0px !important;
    height: 0px !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: visible !important;
    pointer-events: none !important;
}

/* 6. Fullscreen fixed placement for fallback iframe if cross-origin */
iframe[data-testid="stCustomComponentV1"] {
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    width: 100vw !important;
    height: 100vh !important;
    height: 100dvh !important;
    z-index: 0 !important;
    pointer-events: none !important;
    border: none !important;
    margin: 0 !important;
    padding: 0 !important;
    background: transparent !important;
    overflow: hidden !important;
}
</style>
""", unsafe_allow_html=True)


def _render_css_background():
    """Pure CSS pseudo-3D background with animated perspective grid and subtle emerald radial glows."""
    st.markdown("""
<style>
/* CSS Fallback 3D Background */
#msra-css-bg-container {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    height: 100dvh;
    z-index: 0;
    pointer-events: none;
    overflow: hidden;
    background-color: #000000;
}

/* Perspective Plane & Animated Grid */
.msra-grid-plane {
    position: absolute;
    width: 200%;
    height: 200%;
    top: -50%;
    left: -50%;
    background-image:
        linear-gradient(to right, rgba(16, 163, 127, 0.08) 1px, transparent 1px),
        linear-gradient(to bottom, rgba(16, 163, 127, 0.08) 1px, transparent 1px);
    background-size: 50px 50px;
    transform: perspective(600px) rotateX(65deg);
    transform-origin: center center;
    animation: msraGridScroll 22s linear infinite;
    mask-image: radial-gradient(circle at 50% 50%, rgba(0,0,0,0.85) 0%, transparent 75%);
    -webkit-mask-image: radial-gradient(circle at 50% 50%, rgba(0,0,0,0.85) 0%, transparent 75%);
}

@keyframes msraGridScroll {
    0% { background-position: 0 0; }
    100% { background-position: 0 50px; }
}

/* Soft Emerald Radial Glows */
.msra-glow-1 {
    position: absolute;
    top: 15%;
    left: 20%;
    width: 500px;
    height: 500px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(16, 163, 127, 0.12) 0%, rgba(16, 163, 127, 0.03) 45%, transparent 70%);
    filter: blur(40px);
    animation: msraGlowDrift1 18s ease-in-out infinite alternate;
}

.msra-glow-2 {
    position: absolute;
    bottom: 10%;
    right: 15%;
    width: 600px;
    height: 600px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(16, 163, 127, 0.09) 0%, rgba(16, 163, 127, 0.02) 50%, transparent 70%);
    filter: blur(50px);
    animation: msraGlowDrift2 24s ease-in-out infinite alternate;
}

@keyframes msraGlowDrift1 {
    0% { transform: translate(0, 0) scale(1); opacity: 0.7; }
    50% { transform: translate(40px, -30px) scale(1.1); opacity: 1; }
    100% { transform: translate(-20px, 40px) scale(0.95); opacity: 0.6; }
}

@keyframes msraGlowDrift2 {
    0% { transform: translate(0, 0) scale(1); opacity: 0.6; }
    50% { transform: translate(-50px, 20px) scale(1.08); opacity: 0.9; }
    100% { transform: translate(30px, -40px) scale(0.9); opacity: 0.5; }
}

@media (prefers-reduced-motion: reduce) {
    .msra-grid-plane, .msra-glow-1, .msra-glow-2 {
        animation: none !important;
    }
}
</style>

<div id="msra-css-bg-container" aria-hidden="true">
    <div class="msra-grid-plane"></div>
    <div class="msra-glow-1"></div>
    <div class="msra-glow-2"></div>
</div>
""", unsafe_allow_html=True)


def _render_three_background():
    """Renders the 3D particle network (Three.js WebGL with automated HTML5 Canvas 2D
    fallback) and injects the top-left sidebar toggle button.
    """
    three_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <script src="{THREE_JS_CDN}" async></script>
    <style>
        html, body {{
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
            background: transparent;
        }}
        #msra-3d-canvas {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            height: 100dvh;
            pointer-events: none;
            display: block;
            z-index: 0;
        }}
    </style>
</head>
<body>
<script>
(function() {{
    var win = window;
    var doc = document;
    var isParent = false;

    try {{
        if (window.parent && window.parent.document && window.parent.document.body) {{
            doc = window.parent.document;
            win = window.parent;
            isParent = true;
        }}
    }} catch (e) {{
        isParent = false;
    }}

    // Check prefers-reduced-motion
    var prefersReduced = false;
    try {{
        var media = win.matchMedia && win.matchMedia('(prefers-reduced-motion: reduce)');
        prefersReduced = media && media.matches;
    }} catch (e) {{}}

    // Viewport measurement with mobile fallback
    function getViewport() {{
        var w = win.innerWidth || doc.documentElement.clientWidth || (isParent ? 800 : 390);
        var h = win.innerHeight || doc.documentElement.clientHeight || (isParent ? 600 : 844);
        return {{ width: Math.max(w, 320), height: Math.max(h, 320) }};
    }}

    // =========================================================================
    // 1. SIDEBAR REOPEN TOGGLE BUTTON (☰)
    // =========================================================================
    function initSidebarToggle() {{
        var existingBtn = doc.getElementById('msra-sidebar-toggle-btn');
        if (existingBtn) {{
            existingBtn.remove();
        }}

        var btn = doc.createElement('button');
        btn.id = 'msra-sidebar-toggle-btn';
        btn.setAttribute('aria-label', 'Toggle Sidebar');
        btn.setAttribute('title', 'Open Sidebar');
        btn.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="12" x2="20" y2="12"></line><line x1="4" y1="6" x2="20" y2="6"></line><line x1="4" y1="18" x2="20" y2="18"></line></svg>';

        btn.addEventListener('click', function(e) {{
            e.preventDefault();
            e.stopPropagation();

            // 1. Try Streamlit native expand button
            var nativeExpand = doc.querySelector('button[data-testid="stExpandSidebarButton"]') ||
                               doc.querySelector('[data-testid="stSidebarCollapsedControl"] button') ||
                               doc.querySelector('[data-testid="stSidebarCollapsedControl"]');
            if (nativeExpand) {{
                nativeExpand.click();
                return;
            }}

            // 2. Fallback: check sidebar collapse button
            var collapseBtn = doc.querySelector('button[data-testid="stSidebarCollapseButton"]');
            if (collapseBtn) {{
                collapseBtn.click();
            }}
        }});

        btn.addEventListener('touchstart', function(e) {{
            e.preventDefault();
            btn.click();
        }}, {{ passive: false }});

        doc.body.appendChild(btn);

        function updateToggleState() {{
            var sidebar = doc.querySelector('section[data-testid="stSidebar"]');
            var isExpanded = false;

            if (sidebar) {{
                var ariaExp = sidebar.getAttribute('aria-expanded');
                if (ariaExp === 'true') {{
                    isExpanded = true;
                }} else if (ariaExp === 'false') {{
                    isExpanded = false;
                }} else {{
                    var rect = sidebar.getBoundingClientRect();
                    isExpanded = (rect.width > 60 && rect.right > 60);
                }}
            }}

            btn.style.setProperty('display', isExpanded ? 'none' : 'inline-flex', 'important');
        }}

        updateToggleState();

        var observer = new MutationObserver(updateToggleState);
        var observeTarget = doc.querySelector('section[data-testid="stSidebar"]') || doc.body;
        try {{
            observer.observe(observeTarget, {{ attributes: true, attributeFilter: ['aria-expanded', 'style', 'class'] }});
        }} catch(e) {{}}

        win.addEventListener('resize', updateToggleState, {{ passive: true }});
        win.addEventListener('orientationchange', updateToggleState, {{ passive: true }});
        var pollId = setInterval(updateToggleState, 350);

        return function cleanupToggle() {{
            observer.disconnect();
            clearInterval(pollId);
            win.removeEventListener('resize', updateToggleState);
            win.removeEventListener('orientationchange', updateToggleState);
            if (btn && btn.parentNode) btn.remove();
        }};
    }}

    // =========================================================================
    // 2. 3D PARTICLE BACKGROUND (WebGL + Canvas 2D Fallback)
    // =========================================================================
    function initMSRA3D() {{
        // Guard against duplicate active instances
        if (win.__msra_3d_active__ && doc.getElementById('msra-3d-canvas')) {{
            return;
        }}

        // Clean up any existing instances
        if (typeof win.__msra_3d_cleanup__ === 'function') {{
            try {{ win.__msra_3d_cleanup__(); }} catch (e) {{}}
        }}

        var oldCanvas = doc.getElementById('msra-3d-canvas');
        if (oldCanvas) {{
            oldCanvas.remove();
        }}

        // Initialize sidebar reopen button
        var cleanupToggle = initSidebarToggle();

        // Create canvas
        var canvas = doc.createElement('canvas');
        canvas.id = 'msra-3d-canvas';
        canvas.style.position = 'fixed';
        canvas.style.top = '0';
        canvas.style.left = '0';
        canvas.style.width = '100vw';
        canvas.style.height = '100vh';
        canvas.style.height = '100dvh';
        canvas.style.zIndex = '0';
        canvas.style.pointerEvents = 'none';
        canvas.style.display = 'block';

        if (isParent) {{
            doc.body.appendChild(canvas);
        }} else {{
            document.body.appendChild(canvas);
        }}

        var cleanupEngine = null;

        // Check WebGL availability
        var hasWebGL = false;
        try {{
            var testC = doc.createElement('canvas');
            hasWebGL = !!(win.WebGLRenderingContext && (testC.getContext('webgl') || testC.getContext('experimental-webgl')));
        }} catch(e) {{
            hasWebGL = false;
        }}

        // Try Three.js WebGL first if library is available
        if (hasWebGL && typeof THREE !== 'undefined') {{
            try {{
                cleanupEngine = runThreeEngine(canvas);
            }} catch (err) {{
                console.warn('Three.js initialization failed, falling back to Canvas 2D:', err);
                cleanupEngine = runCanvas2DEngine(canvas);
            }}
        }} else {{
            // Wait briefly for Three.js script to load, otherwise launch 2D engine
            var waitCount = 0;
            var maxWait = 25; // 25 * 40ms = 1.0s max wait
            var waitTimer = setInterval(function() {{
                waitCount++;
                if (hasWebGL && typeof THREE !== 'undefined') {{
                    clearInterval(waitTimer);
                    try {{
                        cleanupEngine = runThreeEngine(canvas);
                    }} catch (e) {{
                        cleanupEngine = runCanvas2DEngine(canvas);
                    }}
                }} else if (waitCount >= maxWait) {{
                    clearInterval(waitTimer);
                    // Fall back to robust Canvas 2D engine immediately
                    cleanupEngine = runCanvas2DEngine(canvas);
                }}
            }}, 40);
        }}

        function fullCleanup() {{
            if (typeof cleanupToggle === 'function') cleanupToggle();
            if (typeof cleanupEngine === 'function') cleanupEngine();
            if (win.__msra_3d_active__) {{
                win.__msra_3d_active__ = false;
            }}
        }}

        win.__msra_3d_cleanup__ = fullCleanup;
        win.__msra_3d_active__ = true;
        win.addEventListener('beforeunload', fullCleanup, {{ once: true }});
    }}

    // -------------------------------------------------------------------------
    // THREE.JS WEBGL ENGINE
    // -------------------------------------------------------------------------
    function runThreeEngine(canvas) {{
        var vp = getViewport();
        var isMobile = vp.width < 640;

        var scene = new THREE.Scene();
        var camera = new THREE.PerspectiveCamera(60, vp.width / vp.height, 1, 1500);
        camera.position.z = 450;

        var renderer = new THREE.WebGLRenderer({{
            canvas: canvas,
            alpha: true,
            antialias: true,
            powerPreference: 'low-power'
        }});

        renderer.setSize(vp.width, vp.height);
        var maxDpr = isMobile ? 1.15 : 1.35;
        renderer.setPixelRatio(Math.min(win.devicePixelRatio || 1, maxDpr));
        renderer.setClearColor(0x000000, 0);

        // Dynamically calculate camera visible frustum bounds at z=0 so particles
        // perfectly cover mobile portrait and landscape viewports
        var vFov = (camera.fov * Math.PI) / 180;
        var visH = 2 * Math.tan(vFov / 2) * camera.position.z;
        var visW = visH * camera.aspect;
        var rangeX = visW * 1.15;
        var rangeY = visH * 1.15;
        var rangeZ = 280;

        // Optimized particle count & distance for mobile responsiveness & battery
        var particleCount = isMobile ? 34 : 75;
        var maxDist = isMobile ? 105 : 120;
        var maxDistSq = maxDist * maxDist;

        var positions = new Float32Array(particleCount * 3);
        var velocities = [];

        for (var i = 0; i < particleCount; i++) {{
            positions[i * 3] = (Math.random() - 0.5) * rangeX;
            positions[i * 3 + 1] = (Math.random() - 0.5) * rangeY;
            positions[i * 3 + 2] = (Math.random() - 0.5) * rangeZ;
            velocities.push({{
                x: (Math.random() - 0.5) * 0.20,
                y: (Math.random() - 0.5) * 0.20,
                z: (Math.random() - 0.5) * 0.14
            }});
        }}

        var particleGeo = new THREE.BufferGeometry();
        particleGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));

        // Soft radial glow dot texture
        var dotCanvas = doc.createElement('canvas');
        dotCanvas.width = 32;
        dotCanvas.height = 32;
        var dotCtx = dotCanvas.getContext('2d');
        var grad = dotCtx.createRadialGradient(16, 16, 0, 16, 16, 16);
        grad.addColorStop(0, 'rgba(255, 255, 255, 1)');
        grad.addColorStop(0.35, 'rgba(255, 255, 255, 0.85)');
        grad.addColorStop(0.70, 'rgba(255, 255, 255, 0.25)');
        grad.addColorStop(1, 'rgba(255, 255, 255, 0)');
        dotCtx.fillStyle = grad;
        dotCtx.fillRect(0, 0, 32, 32);
        var dotTexture = new THREE.CanvasTexture(dotCanvas);

        var particleMat = new THREE.PointsMaterial({{
            color: 0x10A37F,
            size: isMobile ? 7 : 8,
            map: dotTexture,
            transparent: true,
            opacity: 0.45,
            blending: THREE.AdditiveBlending,
            depthWrite: false
        }});

        var pointCloud = new THREE.Points(particleGeo, particleMat);
        scene.add(pointCloud);

        // Lines connecting nearby points
        var maxConnections = Math.floor((particleCount * (particleCount - 1)) / 2);
        var linePositions = new Float32Array(maxConnections * 6);
        var lineGeo = new THREE.BufferGeometry();
        lineGeo.setAttribute('position', new THREE.BufferAttribute(linePositions, 3));

        var lineMat = new THREE.LineBasicMaterial({{
            color: 0x10A37F,
            transparent: true,
            opacity: 0.18,
            blending: THREE.AdditiveBlending,
            depthWrite: false
        }});

        var lines = new THREE.LineSegments(lineGeo, lineMat);
        scene.add(lines);

        // Resize and orientation handlers
        function handleResize() {{
            var newVp = getViewport();
            var mob = newVp.width < 640;
            camera.aspect = newVp.width / newVp.height;
            camera.updateProjectionMatrix();
            renderer.setSize(newVp.width, newVp.height);
            renderer.setPixelRatio(Math.min(win.devicePixelRatio || 1, mob ? 1.25 : 1.5));

            var newVisH = 2 * Math.tan(vFov / 2) * camera.position.z;
            var newVisW = newVisH * camera.aspect;
            rangeX = newVisW * 1.15;
            rangeY = newVisH * 1.15;
        }}

        win.addEventListener('resize', handleResize, {{ passive: true }});
        win.addEventListener('orientationchange', function() {{
            setTimeout(handleResize, 100);
            setTimeout(handleResize, 350);
        }}, {{ passive: true }});

        // Mouse and Touch parallax
        var mouseX = 0, mouseY = 0, targetX = 0, targetY = 0;
        function onMouseMove(e) {{
            mouseX = (e.clientX - (vp.width / 2)) * 0.035;
            mouseY = (e.clientY - (vp.height / 2)) * 0.035;
        }}
        win.addEventListener('mousemove', onMouseMove, {{ passive: true }});

        function onTouchMove(e) {{
            if (e.touches && e.touches[0]) {{
                mouseX = (e.touches[0].clientX - (vp.width / 2)) * 0.02;
                mouseY = (e.touches[0].clientY - (vp.height / 2)) * 0.02;
            }}
        }}
        win.addEventListener('touchmove', onTouchMove, {{ passive: true }});

        var isPaused = false;
        function onVisibilityChange() {{
            isPaused = doc.hidden;
        }}
        doc.addEventListener('visibilitychange', onVisibilityChange);

        var animId = null;
        var isDestroyed = false;
        var lastTime = performance.now();
        var targetFPS = isMobile ? 40 : 60;
        var fpsInterval = 1000 / targetFPS;
        var waveAngle = 0;

        function animate(now) {{
            if (isDestroyed) return;
            if (prefersReduced) {{
                renderer.render(scene, camera);
                return;
            }}
            animId = requestAnimationFrame(animate);
            if (isPaused) return;

            var elapsed = now - lastTime;
            if (elapsed < fpsInterval) return;
            lastTime = now - (elapsed % fpsInterval);

            waveAngle += 0.008;
            var posArr = particleGeo.attributes.position.array;

            for (var i = 0; i < particleCount; i++) {{
                posArr[i * 3] += velocities[i].x;
                posArr[i * 3 + 1] += velocities[i].y;
                posArr[i * 3 + 2] += velocities[i].z;

                if (posArr[i * 3] < -rangeX / 2 || posArr[i * 3] > rangeX / 2) velocities[i].x *= -1;
                if (posArr[i * 3 + 1] < -rangeY / 2 || posArr[i * 3 + 1] > rangeY / 2) velocities[i].y *= -1;
                if (posArr[i * 3 + 2] < -rangeZ / 2 || posArr[i * 3 + 2] > rangeZ / 2) velocities[i].z *= -1;
            }}
            particleGeo.attributes.position.needsUpdate = true;

            var lineIndex = 0;
            for (var j = 0; j < particleCount; j++) {{
                var x1 = posArr[j * 3];
                var y1 = posArr[j * 3 + 1];
                var z1 = posArr[j * 3 + 2];
                for (var k = j + 1; k < particleCount; k++) {{
                    var dx = x1 - posArr[k * 3];
                    var dy = y1 - posArr[k * 3 + 1];
                    var dz = z1 - posArr[k * 3 + 2];
                    var distSq = dx * dx + dy * dy + dz * dz;
                    if (distSq < maxDistSq) {{
                        linePositions[lineIndex++] = x1;
                        linePositions[lineIndex++] = y1;
                        linePositions[lineIndex++] = z1;
                        linePositions[lineIndex++] = posArr[k * 3];
                        linePositions[lineIndex++] = posArr[k * 3 + 1];
                        linePositions[lineIndex++] = posArr[k * 3 + 2];
                    }}
                }}
            }}
            lineGeo.setDrawRange(0, lineIndex / 3);
            lineGeo.attributes.position.needsUpdate = true;

            var autoX = Math.sin(waveAngle) * 10;
            var autoY = Math.cos(waveAngle * 0.7) * 7;
            targetX += (mouseX + autoX - targetX) * 0.04;
            targetY += (mouseY + autoY - targetY) * 0.04;

            camera.position.x = targetX;
            camera.position.y = -targetY;
            camera.lookAt(scene.position);

            scene.rotation.y += 0.0005;
            scene.rotation.x += 0.0002;

            renderer.render(scene, camera);
        }}

        if (prefersReduced) {{
            renderer.render(scene, camera);
        }} else {{
            animId = requestAnimationFrame(animate);
        }}

        return function cleanupThree() {{
            isDestroyed = true;
            if (animId) cancelAnimationFrame(animId);
            win.removeEventListener('resize', handleResize);
            win.removeEventListener('orientationchange', handleResize);
            win.removeEventListener('mousemove', onMouseMove);
            win.removeEventListener('touchmove', onTouchMove);
            doc.removeEventListener('visibilitychange', onVisibilityChange);
            try {{
                particleGeo.dispose();
                particleMat.dispose();
                dotTexture.dispose();
                lineGeo.dispose();
                lineMat.dispose();
                renderer.dispose();
            }} catch(e) {{}}
        }};
    }}

    // -------------------------------------------------------------------------
    // HTML5 CANVAS 2D FALLBACK ENGINE (Zero dependencies, 100% mobile-ready)
    // -------------------------------------------------------------------------
    function runCanvas2DEngine(canvas) {{
        var ctx = canvas.getContext('2d');
        if (!ctx) return function() {{}};

        var vp = getViewport();
        var isMobile = vp.width < 640;
        var dpr = Math.min(win.devicePixelRatio || 1, isMobile ? 1.15 : 1.35);

        canvas.width = vp.width * dpr;
        canvas.height = vp.height * dpr;

        var particleCount = isMobile ? 30 : 60;
        var maxDist = isMobile ? 95 : 125;
        var maxDistSq = maxDist * maxDist;

        var particles = [];
        for (var i = 0; i < particleCount; i++) {{
            particles.push({{
                x: Math.random() * vp.width,
                y: Math.random() * vp.height,
                vx: (Math.random() - 0.5) * (isMobile ? 0.35 : 0.45),
                vy: (Math.random() - 0.5) * (isMobile ? 0.35 : 0.45),
                radius: isMobile ? 1.8 : 2.2
            }});
        }}

        function handleResize2D() {{
            var newVp = getViewport();
            var mob = newVp.width < 640;
            dpr = Math.min(win.devicePixelRatio || 1, mob ? 1.25 : 1.5);
            canvas.width = newVp.width * dpr;
            canvas.height = newVp.height * dpr;
        }}

        win.addEventListener('resize', handleResize2D, {{ passive: true }});
        win.addEventListener('orientationchange', function() {{
            setTimeout(handleResize2D, 100);
            setTimeout(handleResize2D, 350);
        }}, {{ passive: true }});

        var isPaused2D = false;
        function onVisChange2D() {{ isPaused2D = doc.hidden; }}
        doc.addEventListener('visibilitychange', onVisChange2D);

        var animId2D = null;
        var isDestroyed2D = false;
        var lastT = performance.now();
        var targetFps = isMobile ? 40 : 60;
        var fpsInt = 1000 / targetFps;

        function drawFrame2D(now) {{
            if (isDestroyed2D) return;
            if (prefersReduced) return;
            animId2D = requestAnimationFrame(drawFrame2D);
            if (isPaused2D) return;

            var el = now - lastT;
            if (el < fpsInt) return;
            lastT = now - (el % fpsInt);

            var curVp = getViewport();
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.save();
            ctx.scale(dpr, dpr);

            for (var i = 0; i < particleCount; i++) {{
                var p = particles[i];
                p.x += p.vx;
                p.y += p.vy;
                if (p.x < 0) p.x = curVp.width;
                else if (p.x > curVp.width) p.x = 0;
                if (p.y < 0) p.y = curVp.height;
                else if (p.y > curVp.height) p.y = 0;

                ctx.beginPath();
                ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
                ctx.fillStyle = 'rgba(16, 163, 127, 0.45)';
                ctx.fill();
            }}

            for (var j = 0; j < particleCount; j++) {{
                var p1 = particles[j];
                for (var k = j + 1; k < particleCount; k++) {{
                    var p2 = particles[k];
                    var dx = p1.x - p2.x;
                    var dy = p1.y - p2.y;
                    var dSq = dx * dx + dy * dy;
                    if (dSq < maxDistSq) {{
                        var alpha = (1 - (dSq / maxDistSq)) * 0.18;
                        ctx.beginPath();
                        ctx.moveTo(p1.x, p1.y);
                        ctx.lineTo(p2.x, p2.y);
                        ctx.strokeStyle = 'rgba(16, 163, 127, ' + alpha.toFixed(3) + ')';
                        ctx.lineWidth = 1;
                        ctx.stroke();
                    }}
                }}
            }}
            ctx.restore();
        }}

        if (prefersReduced) {{
            drawFrame2D(performance.now());
        }} else {{
            animId2D = requestAnimationFrame(drawFrame2D);
        }}

        return function cleanup2D() {{
            isDestroyed2D = true;
            if (animId2D) cancelAnimationFrame(animId2D);
            win.removeEventListener('resize', handleResize2D);
            win.removeEventListener('orientationchange', handleResize2D);
            doc.removeEventListener('visibilitychange', onVisChange2D);
        }};
    }}

    // Start initialization
    initMSRA3D();
}})();
</script>
</body>
</html>
"""
    components.html(three_html, height=0)


def render_background_effect():
    """Main entry point to render the subtle animated background effect.
    Returns immediately if ENABLE_3D_BACKGROUND is False.
    """
    if not ENABLE_3D_BACKGROUND:
        return

    _inject_surface_transparency()

    if BACKGROUND_STYLE == "three":
        _render_three_background()
    elif BACKGROUND_STYLE == "css":
        _render_css_background()
