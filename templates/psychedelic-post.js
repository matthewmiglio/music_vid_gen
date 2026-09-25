// WebGL2 psychedelic post pass over the drawn scene canvases.
// Stack: mirror symmetry -> kaleidoscope fold -> droste (fractal zoom) portal -> liquid domain warp
// -> morph between two scenes (noise melt / luminance burn-through / upward smoke melt)
// -> RGB split -> echo ghosts -> neon edges -> hue cycle -> gradient map -> solarize -> grain/vignette.
// Every uniform is a pure function of time, so any frame renders identically in isolation.
(function () {
  const VS = `#version 300 es
  in vec2 p; out vec2 uv;
  void main(){ uv = p*0.5+0.5; gl_Position = vec4(p,0.,1.); }`;
  const FS = `#version 300 es
  precision highp float;
  uniform sampler2D A; uniform sampler2D B;
  uniform float mixT, mode, time, warp, warpF, kal, kalN, kalRot, kalA, mirX, mirXc, mirY, mirYc;
  uniform float dro, droZ, droSpin, echo, echoZ, echoHue, hue, hueAmt, gmap, gPhase, gFreq, solar, rgb;
  uniform float edge, edgeHue, sat, grain, frame, flash, fade, vig;
  uniform vec2 kalC, droC, echoOff, echoC;
  uniform vec3 pa, pb, pc, pd;
  in vec2 uv; out vec4 o;
  const vec2 AR = vec2(1.7777778, 1.);
  const float TAU = 6.2831853;
  float h(vec2 p){ return fract(sin(dot(p, vec2(127.1,311.7)))*43758.5453); }
  float n(vec2 p){ vec2 i=floor(p), f=fract(p); f=f*f*(3.-2.*f);
    return mix(mix(h(i),h(i+vec2(1,0)),f.x), mix(h(i+vec2(0,1)),h(i+vec2(1,1)),f.x), f.y); }
  float fbm(vec2 p){ float s=0., a=.5; for(int i=0;i<4;i++){ s+=a*n(p); p*=2.03; a*=.5; } return s/.9375; }
  vec3 hueRot(vec3 c, float a){ const vec3 k = vec3(0.57735); float ca=cos(a);
    return c*ca + cross(k,c)*sin(a) + k*dot(k,c)*(1.-ca); }
  float lum(vec3 c){ return dot(c, vec3(.299,.587,.114)); }
  // centred, aspect-correct space: x in [-.889,.889], y in [-.5,.5] (y up)
  vec2 toP(vec2 u){ return (u-.5)*AR; }
  vec2 toU(vec2 P){ return P/AR+.5; }
  vec2 foldU(vec2 q){ q = abs(mod(q, 2.)); return 1. - abs(1. - q); } // mirrored wrap keeps edges seamless
  float m = 0.;
  vec3 SA(vec2 q){ return texture(A, foldU(q)).rgb; }
  vec3 S(vec2 q){
    q = foldU(q);
    if (mixT <= 0.) return texture(A,q).rgb;
    if (mixT >= 1.) return texture(B,q).rgb;
    return mix(texture(A,q).rgb, texture(B,q).rgb, m);
  }
  void main(){
    vec2 P = toP(uv);
    // --- mirror symmetry (hard fold; sign picks which half is kept)
    if (mirX > .5)  P.x = mirXc + abs(P.x - mirXc);
    if (mirX < -.5) P.x = mirXc - abs(P.x - mirXc);
    if (mirY > .5 && P.y < mirYc) { float d = mirYc - P.y; P.y = mirYc + d; P.x += .012*sin(d*90. - time*4.)*smoothstep(0.,.08,d); }
    // --- droste portal: recursive copies of the frame zooming into droC
    if (dro > 0.) {
      vec2 v = P - droC; float r = length(v) + 1e-5;
      float R = dro * 1.25;
      float w = 1. - smoothstep(R*.8, R, r);
      if (w > 0.) {
        float K = log(2.2), R0 = .16;
        float lr = log(r) - log(R0) + droZ;
        float k = floor(lr / K);
        float lr2 = lr - k*K;
        float r2 = R0 * exp(lr2);
        float a = atan(v.y, v.x) + droSpin * k + droSpin*.35*lr2;
        vec2 pd2 = droC + r2*vec2(cos(a), sin(a));
        P = mix(P, pd2, w);
      }
    }
    // --- kaleidoscope: fold angle into a mirrored wedge, blend coordinates by kal
    if (kal > 0.) {
      vec2 v = P - kalC; float r = length(v); float a = atan(v.y, v.x) + kalRot;
      float seg = TAU / kalN; a = mod(a, seg); a = abs(a - seg*.5);
      vec2 pk = kalC + r*vec2(cos(kalA + a), sin(kalA + a));
      P = mix(P, pk, kal);
    }
    // --- liquid domain warp
    vec2 wq = vec2(fbm(P*warpF + vec2(time*.13, 0.)), fbm(P*warpF + vec2(5.2,1.3) - vec2(0., time*.11)));
    vec2 d = (wq - .5) * warp;
    d += warp*.18*vec2(sin(P.y*11. + time*1.9), cos(P.x*8. - time*1.6));
    vec2 q = toU(P + d);
    // --- morph mask
    float seam = 0.;
    if (mixT > 0. && mixT < 1.) {
      if (mode < .5) { // noise melt
        float nn = fbm(P*3.1 + wq*1.5);
        m = smoothstep(nn - .07, nn + .07, mixT*1.3 - .15);
      } else if (mode < 1.5) { // burn-through where A is bright
        float la = lum(SA(q));
        float nn = fbm(P*4. + time);
        m = smoothstep(.0, .12, la*1.6 + mixT*1.25 - 1.05 + (nn-.5)*.25);
        m = max(m, smoothstep(.75, 1., mixT));
      } else { // upward smoke melt: A rises and boils away, B condenses from the top
        float nn = fbm(vec2(P.x*3.2, P.y*1.4 - time*.8) + wq);
        m = smoothstep(nn - .08, nn + .08, mixT*1.35 - .2 + (P.y)*.35);
        q.y -= mixT*(1.-m)*.14*(.5+nn);
        q.x += (nn-.5)*.05*mixT;
      }
      seam = m*(1.-m)*4.;
    }
    // --- chromatic split
    vec2 dir = P * rgb + d*rgb*18.;
    vec3 c;
    c.r = S(q + dir/AR).r;
    vec3 g0 = S(q);
    c.g = g0.g;
    c.b = S(q - dir/AR).b;
    // --- echo ghosts (hue-shifted copies, lighten blend)
    if (echo > 0.) {
      vec2 EC = toU(echoC);
      for (int i = 1; i <= 3; i++) {
        float fi = float(i);
        vec2 qi = EC + (q - EC)*(1. - fi*echoZ) + fi*echoOff;
        vec3 e = hueRot(S(qi), fi*echoHue);
        float el = lum(e);
        e *= smoothstep(.3, .75, el) * smoothstep(-.02, .12, el - lum(c)); // only highlights leave ghosts
        c = max(c, e * echo * pow(.62, fi-1.));
      }
    }
    // --- neon edges
    if (edge > 0.) {
      float l0 = lum(g0);
      float lx = lum(S(q + vec2(2.2/1920., 0.))), ly = lum(S(q + vec2(0., 2.2/1080.)));
      float e = smoothstep(.02, .14, abs(lx-l0) + abs(ly-l0));
      vec3 ec = .55 + .45*cos(TAU*(vec3(0.,.33,.67) + edgeHue + l0*.8));
      c += ec * e * edge;
    }
    // --- hue cycling
    c = mix(c, clamp(hueRot(c, hue), 0., 1.), hueAmt);
    // --- gradient map (cosine palette over luminance), keeps shading
    float L = lum(c);
    vec3 gm = pa + pb*cos(TAU*(pc*(L*gFreq) + pd + gPhase));
    gm *= .35 + .9*L;
    c = mix(c, clamp(gm, 0., 1.), gmap);
    // --- solarize
    vec3 sc = mix(c, 1. - c, smoothstep(.42, .62, c));
    c = mix(c, sc*1.25, solar);
    // --- saturation
    float l2 = lum(c); c = mix(vec3(l2), c, sat);
    // --- morph seam glow (cyan / ultraviolet)
    c += mix(vec3(.5,.88,.84), vec3(.75,.3,.85), .5+.5*sin(time*3.)) * seam * seam * .5;
    // --- contrast
    c = clamp((c - .5)*1.14 + .5, 0., 1.);
    c = pow(c, vec3(.94));
    // --- flash, vignette, grain, fade
    c = mix(c, vec3(.93,.9,.85), flash);
    vec2 vv = uv - .5; c *= 1. - dot(vv*vec2(1.1,1.4), vv*vec2(1.1,1.4)) * vig;
    c += (h(uv*vec2(1920.,1080.) + frame*17.13) - .5) * grain;
    c = mix(c, vec3(.039,.051,.12), fade);
    o = vec4(c, 1.);
  }`;

  const NAMES = ["mixT", "mode", "time", "warp", "warpF", "kal", "kalN", "kalRot", "kalA", "mirX", "mirXc", "mirY", "mirYc",
    "dro", "droZ", "droSpin", "echo", "echoZ", "echoHue", "hue", "hueAmt", "gmap", "gPhase", "gFreq", "solar", "rgb",
    "edge", "edgeHue", "sat", "grain", "frame", "flash", "fade", "vig"];
  const V2 = ["kalC", "droC", "echoOff", "echoC"], V3 = ["pa", "pb", "pc", "pd"];
  let gl, U = {}, texA, texB;
  function sh(type, src) {
    const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
    return s;
  }
  function mkTex(unit) {
    const t = gl.createTexture(); gl.activeTexture(gl.TEXTURE0 + unit); gl.bindTexture(gl.TEXTURE_2D, t);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    return t;
  }
  function init(canvas) {
    gl = canvas.getContext("webgl2", { preserveDrawingBuffer: true, antialias: false, premultipliedAlpha: false });
    const prog = gl.createProgram();
    gl.attachShader(prog, sh(gl.VERTEX_SHADER, VS)); gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, FS));
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(prog));
    gl.useProgram(prog);
    const b = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, b);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(prog, "p"); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    ["A", "B", ...NAMES, ...V2, ...V3].forEach((k) => (U[k] = gl.getUniformLocation(prog, k)));
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
    texA = mkTex(0); texB = mkTex(1);
    gl.uniform1i(U.A, 0); gl.uniform1i(U.B, 1);
    gl.viewport(0, 0, canvas.width, canvas.height);
  }
  function render(srcA, srcB, P) {
    let mixT = P.mixT || 0;
    gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, texA);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, srcA);
    if (srcB && mixT > 0) {
      gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, texB);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, srcB);
    } else mixT = 0;
    gl.uniform1f(U.mixT, mixT);
    for (const k of NAMES) if (k !== "mixT") gl.uniform1f(U[k], P[k] || 0);
    for (const k of V2) { const v = P[k] || [0, 0]; gl.uniform2f(U[k], v[0], v[1]); }
    for (const k of V3) { const v = P[k] || [0, 0, 0]; gl.uniform3f(U[k], v[0], v[1], v[2]); }
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  }
  window.POST = { init, render };
})();
