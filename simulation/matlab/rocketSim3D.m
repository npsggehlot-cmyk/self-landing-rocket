function out = rocketSim3D(varargin)
% ROCKETSIM3D  3D flight simulator for the self-landing TVC rocket (RocketFC v2.1).
%   Run:  rocketSim3D            (MATLAB R2016b+ or GNU Octave 6+)
%   Same PID as the flight firmware: gimbal = -(Kp*tilt + Ki*integral(tilt) + Kd*rate)
%   Landing: the 2nd F15 is commanded LANDING DELAY seconds after apogee,
%            thrust starts IGNITER DELAY later. "Auto-find" searches for the
%            softest-landing delay. Parachute mode is the first-flight profile.
%   Physics: 3D translation + pitch/yaw rotation, Estes F15 thrust curve,
%            propellant burn-off, drag, CP/CG normal force, aero damping,
%            wind + gusts, thrust misalignment, servo lag + rate limit,
%            200 Hz controller with sensor noise, 1 m launch rail.

if nargin > 0 && strcmp(varargin{1}, 'selftest'), out = selfTest(varargin{2:end}); return; end
fig = figure('Name', 'RocketFC 3D Flight Sim', 'NumberTitle', 'off', 'Color', [0.97 0.97 0.98], ...
             'Units', 'normalized', 'Position', [0 0 1 1]);
try, theme(fig, 'light'); catch, end                  % MATLAB R2025a+ dark mode -> light plots
try, set(fig, 'WindowState', 'maximized'); catch, end % fit the browser / screen
ui.fig = fig;

% ---------------- parameter panel ----------------
F = { % label,                       key,         default
  'CONTROL (firmware PID)',           '',           []
  'Kp  (gimbal deg / deg)',           'kp',         0.30
  'Ki  (gimbal deg / deg*s)',         'ki',         0.05
  'Kd  (gimbal deg / deg/s)',         'kd',         0.08
  'Gimbal limit (deg)',               'gimMax',     5
  'Servo lag (s)',                    'servoTau',   0.03
  'Servo rate limit (deg/s)',         'servoRate',  150
  'LANDING',                          '',           []
  'Landing delay after apogee (s)',   'landDelay',  1.76
  'Igniter delay (s)',                'ignDelay',   0.35
  'VEHICLE',                          '',           []
  'Liftoff mass, both motors (kg)',   'mass',       1.00
  'Length (m)',                       'len',        0.70
  'CG to gimbal (m)',                 'cgGimbal',   0.30
  'CP ahead of CG (m, + = unstable)', 'cpOffset',   0.05
  'Drag coefficient Cd',              'cd',         0.60
  'ENVIRONMENT',                      '',           []
  'Wind speed (m/s)',                 'wind',       2.0
  'Gust strength (m/s)',              'gust',       0.5
  'Launch rail tilt (deg)',           'railAngle',  3
  'Thrust misalignment (deg)',        'misalign',   0.5
  'Random seed',                      'seed',       1
};
pnl = uipanel(fig, 'Units', 'normalized', 'Position', [0.005 0.01 0.205 0.98], ...
              'Title', 'Flight parameters', 'BackgroundColor', [0.97 0.97 0.98]);
nrow = size(F, 1) + 7;  y = 1;  h = 1 / nrow;
for i = 1:size(F, 1)
  y = y - h;
  if isempty(F{i, 2})
    uicontrol(pnl, 'Style', 'text', 'Units', 'normalized', 'Position', [0.03 y 0.94 h*0.9], ...
              'String', F{i, 1}, 'FontWeight', 'bold', 'HorizontalAlignment', 'left', ...
              'BackgroundColor', [0.97 0.97 0.98]);
  else
    uicontrol(pnl, 'Style', 'text', 'Units', 'normalized', 'Position', [0.03 y 0.66 h*0.9], ...
              'String', F{i, 1}, 'HorizontalAlignment', 'left', 'BackgroundColor', [0.97 0.97 0.98]);
    ui.(F{i, 2}) = uicontrol(pnl, 'Style', 'edit', 'Units', 'normalized', ...
              'Position', [0.70 y+h*0.05 0.27 h*0.9], 'String', num2str(F{i, 3}), 'BackgroundColor', 'w');
  end
end
y = y - h;
uicontrol(pnl, 'Style', 'text', 'Units', 'normalized', 'Position', [0.03 y 0.30 h*0.9], ...
          'String', 'Mode', 'HorizontalAlignment', 'left', 'BackgroundColor', [0.97 0.97 0.98]);
ui.mode = uicontrol(pnl, 'Style', 'popupmenu', 'Units', 'normalized', 'Position', [0.33 y+h*0.05 0.64 h*0.9], ...
          'String', {'Propulsive landing', 'Parachute (first flight)'}, 'Value', 1);
y = y - h;
ui.noise = uicontrol(pnl, 'Style', 'checkbox', 'Units', 'normalized', 'Position', [0.03 y 0.94 h*0.9], ...
          'String', 'Sensor noise', 'Value', 1, 'BackgroundColor', [0.97 0.97 0.98]);
y = y - h;
uicontrol(pnl, 'Style', 'text', 'Units', 'normalized', 'Position', [0.03 y 0.40 h*0.9], ...
          'String', 'Playback speed', 'HorizontalAlignment', 'left', 'BackgroundColor', [0.97 0.97 0.98]);
ui.speed = uicontrol(pnl, 'Style', 'popupmenu', 'Units', 'normalized', 'Position', [0.45 y+h*0.05 0.52 h*0.9], ...
          'String', {'0.25x', '0.5x', '1x (real time)', '2x', '4x'}, 'Value', 3);
y = y - 1.5*h;
uicontrol(pnl, 'Style', 'pushbutton', 'Units', 'normalized', 'Position', [0.03 y 0.94 h*1.3], ...
          'String', 'SIMULATE + PLAY', 'FontWeight', 'bold', 'Callback', @(s, e) onRun(fig));
y = y - 1.5*h;
uicontrol(pnl, 'Style', 'pushbutton', 'Units', 'normalized', 'Position', [0.03 y 0.46 h*1.3], ...
          'String', 'Replay', 'Callback', @(s, e) onReplay(fig));
uicontrol(pnl, 'Style', 'pushbutton', 'Units', 'normalized', 'Position', [0.51 y 0.46 h*1.3], ...
          'String', 'Auto-find delay', 'Callback', @(s, e) onAutoDelay(fig));

% ---------------- plots ----------------
ui.ax3 = axes('Parent', fig, 'Position', [0.25 0.30 0.38 0.66]);
ui.axC = axes('Parent', fig, 'Position', [0.66 0.55 0.32 0.41]);
ui.axH = axes('Parent', fig, 'Position', [0.68 0.395 0.30 0.115]);
ui.axV = axes('Parent', fig, 'Position', [0.68 0.235 0.30 0.115]);
ui.axA = axes('Parent', fig, 'Position', [0.68 0.055 0.30 0.115]);
ui.res = uicontrol(fig, 'Style', 'text', 'Units', 'normalized', 'Position', [0.25 0.01 0.38 0.22], ...
          'String', 'Press SIMULATE + PLAY', 'HorizontalAlignment', 'left', 'FontName', 'Courier', ...
          'FontSize', 10, 'BackgroundColor', [1 1 1]);
ui.slider = uicontrol(fig, 'Style', 'slider', 'Units', 'normalized', 'Position', [0.25 0.24 0.38 0.025], ...
          'Min', 0, 'Max', 1, 'Value', 0, 'Callback', @(s, e) onScrub(fig));
ui.sim = [];
set(fig, 'UserData', ui);
onRun(fig);
end

% =====================================================================================
function P = readParams(ui)
keys = {'kp','ki','kd','gimMax','servoTau','servoRate','landDelay','ignDelay','mass','len', ...
        'cgGimbal','cpOffset','cd','wind','gust','railAngle','misalign','seed'};
for i = 1:numel(keys)
  v = str2double(get(ui.(keys{i}), 'String'));
  if isnan(v), error('Parameter "%s" is not a number', keys{i}); end
  P.(keys{i}) = v;
end
P.chuteMode = get(ui.mode, 'Value') == 2;
P.noise = get(ui.noise, 'Value') == 1;
P.diam = 0.0762;                    % Apogee 3in body tube
end

function onRun(fig)
ui = get(fig, 'UserData');
P = readParams(ui);
set(ui.res, 'String', 'Simulating...'); drawnow;
ui.sim = simulateFlight(P, 0.001, 20);
ui.P = P;
set(fig, 'UserData', ui);
drawScene(fig);
animate(fig);
end

function onReplay(fig)
ui = get(fig, 'UserData');
if ~isempty(ui.sim), animate(fig); end
end

function onScrub(fig)
ui = get(fig, 'UserData');
if isempty(ui.sim), return; end
k = max(1, round(get(ui.slider, 'Value') * (numel(ui.sim.t) - 1)) + 1);
drawFrame(fig, k);
end

function onAutoDelay(fig)
ui = get(fig, 'UserData');
P = readParams(ui);
P.chuteMode = false;  set(ui.mode, 'Value', 1);
set(ui.res, 'String', 'Searching for the softest landing delay...'); drawnow;
[best, v] = findBestDelay(P);
set(ui.landDelay, 'String', sprintf('%.2f', best));
set(ui.res, 'String', sprintf('Best landing delay = %.2f s  (touchdown %.2f m/s)\nRunning it...', best, v)); drawnow;
onRun(fig);
end

function [best, vbest] = findBestDelay(P)
% coarse sweep (0.25 s) then golden-section refine; score = touchdown speed
ds = 0:0.25:6;  c = zeros(size(ds));
for i = 1:numel(ds), c(i) = landingScore(P, ds(i)); end
[~, i] = min(c);  a = max(0, ds(i) - 0.25);  b = ds(i) + 0.25;  gr = (sqrt(5) - 1) / 2;
x1 = b - gr * (b - a); x2 = a + gr * (b - a); f1 = landingScore(P, x1); f2 = landingScore(P, x2);
while b - a > 0.01
  if f1 < f2, b = x2; x2 = x1; f2 = f1; x1 = b - gr * (b - a); f1 = landingScore(P, x1);
  else,       a = x1; x1 = x2; f1 = f2; x2 = a + gr * (b - a); f2 = landingScore(P, x2); end
end
best = ds(i); vbest = c(i);                       % the curve has a cliff at the optimum,
for d = round((a + b) / 2 * 100) / 100 + (-0.05:0.01:0.05)   % so finish with a 0.01 s scan
  if d < 0, continue; end
  v = landingScore(P, d);
  if v < vbest, best = d; vbest = v; end
end
end

function s = landingScore(P, d)
P.landDelay = d;
S = simulateFlight(P, 0.001, 1000);
s = norm(S.touchVel);
end

% =====================================================================================
function S = simulateFlight(P, dt, logEvery)
g = 9.80665; rho = 1.225;
Sref = pi * P.diam^2 / 4;  CNa = 2.0;              % body normal-force slope (1/rad)
mProp = 0.060; Itot = 49.6;                         % Estes F15 propellant (kg), total impulse (N s)
Iperp = P.mass * P.len^2 / 12;                      % pitch/yaw inertia (uniform rod)
railLen = 1.0; tEnd = 45;
rngSaved = rng; rng(P.seed);

% state
th = P.railAngle * pi / 180;
q = [cos(th/2); 0; sin(th/2); 0];                   % tilt the rail toward +x (downwind)
pos = [0; 0; 0]; vel = [0; 0; 0]; w = [0; 0; 0];
m = P.mass; gim = [0; 0]; gimCmd = [0; 0]; ix = 0; iy = 0; gust = [0; 0];
phase = 0;            % 0 pad/rail, 1 ascent burn, 2 coast, 3 descent, 4 landing burn, 5 chute, 6 down
tvcOn = false; liftCnt = 0; tApo = NaN; tCmd = NaN; tIgn2 = inf; tChute = NaN; tLegs = NaN;
ctrlEvery = max(1, round(0.005 / dt)); nStep = round(tEnd / dt);
nLog = floor(nStep / logEvery) + 1;
L.t = zeros(1, nLog); L.pos = zeros(3, nLog); L.vel = zeros(3, nLog); L.q = zeros(4, nLog);
L.gim = zeros(2, nLog); L.T = zeros(1, nLog); L.phase = zeros(1, nLog); L.tilt = zeros(3, nLog);
L.legs = zeros(1, nLog); L.chute = zeros(1, nLog); L.m = zeros(1, nLog);
li = 0; maxTiltAsc = 0; maxGim = 0; S.ign2State = [NaN NaN]; touchVel = [0; 0; 0]; touchTilt = 0;
chuteCdA = 2 * (P.mass - mProp) * g / (rho * 5^2);  % ~5 m/s descent

for n = 0:nStep
  t = n * dt;
  R = q2R(q); b = R(:, 3);
  T1 = f15(t); T2 = f15(t - tIgn2); T = T1 + T2;
  % wind with first-order gusts
  gust = gust + (-gust * dt + P.gust * sqrt(2 * dt) * randn(2, 1));
  windV = [P.wind + gust(1); gust(2); 0];
  vrel = vel - windV; V = norm(vrel);
  Fdrag = -0.5 * rho * P.cd * Sref * V * vrel;
  vperp = vrel - (vrel' * b) * b;
  FN = -0.5 * rho * CNa * Sref * V * vperp;          % normal force at the CP
  if ~isnan(tChute) && t > tChute
    k = min(1, (t - tChute) / 0.8);                  % canopy inflation
    Fdrag = Fdrag - 0.5 * rho * chuteCdA * k * V * vrel;
  end
  ga = (gim + [P.misalign; 0]) * pi / 180;
  fb = [-sin(ga(2)); sin(ga(1)); 1]; fb = fb / norm(fb);
  Fth = T * (R * fb);
  Fsf = Fth + Fdrag + FN;                            % specific-force part (what the IMU feels)
  F = Fsf + [0; 0; -m * g];
  tau = cross([0; 0; -P.cgGimbal], T * fb) + cross([0; 0; P.cpOffset], R' * FN);
  tau(1:2) = tau(1:2) - 0.5 * rho * V * Sref * CNa * (P.len / 2)^2 * w(1:2);   % aero damping
  tau(3) = 0;

  % ---------- flight computer (200 Hz), same logic as RocketFC.ino ----------
  if mod(n, ctrlEvery) == 0
    u = R' * [0; 0; 1];
    tiltX = atan2(u(2), u(3)) * 180 / pi; tiltY = atan2(-u(1), u(3)) * 180 / pi;
    wd = w * 180 / pi;
    if P.noise
      tiltX = tiltX + 0.15 * randn; tiltY = tiltY + 0.15 * randn; wd = wd + 0.3 * randn(3, 1);
    end
    sfz = (b' * Fsf) / (m * g);                      % body-axis accelerometer (g)
    if phase <= 1 && ~tvcOn
      if T > 0 && sfz > 1.5, liftCnt = liftCnt + 1; else liftCnt = 0; end
      if liftCnt >= 10, tvcOn = true; ix = 0; iy = 0; end          % 50 ms > 1.5 g
    end
    if phase == 1 && t > 0.5 && sfz < 0.3, tvcOn = false; end       % burnout
    if tvcOn
      cdt = ctrlEvery * dt;
      ix = min(20, max(-20, ix + tiltX * cdt)); iy = min(20, max(-20, iy + tiltY * cdt));
      cx = -(P.kp * tiltX + P.ki * ix + P.kd * wd(1));
      cy = -(P.kp * tiltY + P.ki * iy + P.kd * wd(2));
      gimCmd = min(P.gimMax, max(-P.gimMax, [cx; cy]));
    else
      gimCmd = [0; 0];
    end
  end
  % servo: rate limit + first-order lag
  dg = (gimCmd - gim) * dt / max(P.servoTau, dt);
  dg = max(-P.servoRate * dt, min(P.servoRate * dt, dg));
  gim = gim + dg;

  % ---------- dynamics ----------
  if phase == 0                                      % on the pad / rail
    ab = (b' * F) / m;
    if T > 0 && (ab > 0 || (vel' * b) > 0)
      vb = max(0, vel' * b + ab * dt);
      vel = vb * b; pos = pos + vel * dt;
      if pos' * b > railLen, phase = 1; end
    end
    w = [0; 0; 0];
  else
    vel = vel + F / m * dt; pos = pos + vel * dt;
    w = w + tau / Iperp * dt;
    q = qStep(q, w, dt);
  end
  m = m - mProp / Itot * T * dt;

  % ---------- flight events ----------
  if phase == 1 && t > 3.5, phase = 2; end
  if phase == 2 && vel(3) <= 0
    tApo = t; phase = 3;
    if P.chuteMode, tChute = t + 0.2; phase = 5;
    else, tCmd = t + P.landDelay; end
  end
  if phase == 3 && t >= tCmd
    phase = 4; tIgn2 = tCmd + P.ignDelay; tLegs = tCmd; tvcOn = true; ix = 0; iy = 0;
    S.ign2State = [pos(3), vel(3)];
  end
  if phase == 4 && t > tIgn2 + 3.6, tvcOn = false; end
  if phase == 5 && isnan(tLegs) && pos(3) < 20 && t > tChute + 1, tLegs = t; end
  if phase >= 1, maxGim = max(maxGim, max(abs(gim))); end
  if phase == 1, maxTiltAsc = max(maxTiltAsc, acos(min(1, b(3))) * 180 / pi); end

  if mod(n, logEvery) == 0 || (phase > 0 && pos(3) < 0)
    li = li + 1;
    L.t(li) = t; L.pos(:, li) = pos; L.vel(:, li) = vel; L.q(:, li) = q; L.gim(:, li) = gim;
    L.T(li) = T; L.phase(li) = phase; L.m(li) = m;
    u = R' * [0; 0; 1];
    L.tilt(:, li) = [atan2(u(2), u(3)); atan2(-u(1), u(3)); acos(min(1, b(3)))] * 180 / pi;
    L.legs(li) = ~isnan(tLegs) && t >= tLegs; L.chute(li) = ~isnan(tChute) && t >= tChute;
  end
  if phase > 0 && pos(3) < 0 && t > 0.5              % touchdown
    touchVel = vel; touchTilt = acos(min(1, b(3))) * 180 / pi; phase = 6; L.phase(li) = 6;
    break;
  end
end
f = fieldnames(L);
for i = 1:numel(f), L.(f{i}) = L.(f{i})(:, 1:li); end
S = mergeStruct(S, L);
S.tApo = tApo; S.tCmd = tCmd; S.tIgn2 = tIgn2; S.touchVel = touchVel; S.touchTilt = touchTilt;
S.apogee = max(L.pos(3, :)); S.maxTiltAsc = maxTiltAsc; S.maxGim = maxGim; S.landed = phase == 6;
S.chuteMode = P.chuteMode; S.tLegs = tLegs; S.tChute = tChute;
rng(rngSaved);
end

function T = f15(tb)       % Estes F15 thrust curve (49.6 N s, 25.3 N peak, 3.45 s)
persistent ct cf
if isempty(ct)
  ct = [0 0.063 0.118 0.158 0.228 0.34 0.386 0.425 0.481 0.583 0.883 1.191 1.364 1.569 1.727 ...
        2.066 2.347 2.662 2.906 3.08 3.223 3.316 3.358 3.4 3.427 3.45];
  cf = [0 2.13 4.41 8.36 13.68 20.82 25.3 24.9 22.19 17.93 16.01 14.50 15.26 15.56 14.65 ...
        14.19 13.90 13.75 13.44 13.29 13.59 13.44 10.87 7.85 3.47 0];
end
if tb <= 0 || tb >= 3.45, T = 0; return; end
i = 2; while ct(i) < tb, i = i + 1; end
T = cf(i-1) + (cf(i) - cf(i-1)) * (tb - ct(i-1)) / (ct(i) - ct(i-1));
end

function R = q2R(q)
a = q(1); b = q(2); c = q(3); d = q(4);
R = [1-2*(c^2+d^2), 2*(b*c-a*d),   2*(b*d+a*c);
     2*(b*c+a*d),   1-2*(b^2+d^2), 2*(c*d-a*b);
     2*(b*d-a*c),   2*(c*d+a*b),   1-2*(b^2+c^2)];
end

function q = qStep(q, w, dt)
k = 0.5 * dt; wx = w(1) * k; wy = w(2) * k; wz = w(3) * k;
q = [q(1) - q(2)*wx - q(3)*wy - q(4)*wz;
     q(2) + q(1)*wx + q(3)*wz - q(4)*wy;
     q(3) + q(1)*wy + q(4)*wx - q(2)*wz;
     q(4) + q(1)*wz + q(2)*wy - q(3)*wx];
q = q / norm(q);
end

function A = mergeStruct(A, B)
f = fieldnames(B);
for i = 1:numel(f), A.(f{i}) = B.(f{i}); end
end

% =====================================================================================
function drawScene(fig)
ui = get(fig, 'UserData'); S = ui.sim; P = ui.P;
phaseCol = [0.20 0.45 0.90; 0.20 0.45 0.90; 0.55 0.55 0.60; 0.55 0.30 0.75; 0.95 0.45 0.10; 0.20 0.65 0.35; 0.2 0.2 0.2];

% ---- overview ----
ax = ui.ax3; cla(ax); hold(ax, 'on');
xr = [min(S.pos(1, :)) max(S.pos(1, :))]; yr = [min(S.pos(2, :)) max(S.pos(2, :))];
span = max([diff(xr), diff(yr), 20]);
cx = mean(xr); cy = mean(yr);
gx = linspace(cx - span*0.7, cx + span*0.7, 15); gy = linspace(cy - span*0.7, cy + span*0.7, 15);
[GX, GY] = meshgrid(gx, gy);
surface(GX, GY, zeros(size(GX)), 'Parent', ax, 'FaceColor', [0.80 0.90 0.78], 'EdgeColor', [0.65 0.78 0.63]);
for ph = 0:6
  idx = find(S.phase == ph);
  if isempty(idx), continue; end
  idx = [max(1, idx(1) - 1) idx];
  plot3(ax, S.pos(1, idx), S.pos(2, idx), S.pos(3, idx), '-', 'Color', phaseCol(ph + 1, :), 'LineWidth', 2);
end
[~, ia] = max(S.pos(3, :));
plot3(ax, S.pos(1, ia), S.pos(2, ia), S.pos(3, ia), 'k^', 'MarkerFaceColor', 'y', 'MarkerSize', 8);
text(S.pos(1, ia), S.pos(2, ia), S.pos(3, ia) + 2, sprintf(' apogee %.1f m', S.apogee), 'Parent', ax);
if ~isnan(S.tCmd) && S.tIgn2 <= S.t(end)
  [~, ic] = min(abs(S.t - S.tIgn2));
  plot3(ax, S.pos(1, ic), S.pos(2, ic), S.pos(3, ic), 'ko', 'MarkerFaceColor', [1 0.5 0], 'MarkerSize', 8);
  text(S.pos(1, ic), S.pos(2, ic), S.pos(3, ic), sprintf('  motor 2 lights (%.1f m)', S.pos(3, ic)), 'Parent', ax);
end
plot3(ax, 0, 0, 0, 'ks', 'MarkerFaceColor', 'k');
zmax = max(10, S.apogee * 1.12);
axis(ax, 'equal'); xlim(ax, [gx(1) gx(end)]); ylim(ax, [gy(1) gy(end)]); zlim(ax, [0 zmax]);
grid(ax, 'on'); view(ax, 38, 16); xlabel(ax, 'x downwind (m)'); ylabel(ax, 'y (m)'); zlabel(ax, 'altitude (m)');
title(ax, 'Flight path   (blue = boost, grey = coast, purple = fall, orange = landing burn, green = chute)');
ui.hOver = makeRocket(ax, 8);                       % drawn 8x size so it's visible
hold(ax, 'off');

% ---- chase cam (true size) ----
ax = ui.axC; cla(ax); hold(ax, 'on');
[GX, GY] = meshgrid(-60:2:60, -60:2:60);
surface(GX, GY, zeros(size(GX)), 'Parent', ax, 'FaceColor', [0.80 0.90 0.78], 'EdgeColor', [0.62 0.75 0.60], ...
        'FaceLighting', 'none');
ui.hChase = makeRocket(ax, 1);
axis(ax, 'equal'); grid(ax, 'on'); view(ax, 30, 12);
title(ax, 'Chase cam (true size)'); hold(ax, 'off');
lighting(ax, 'gouraud'); camlight(ax, 'headlight');

% ---- time plots ----
tp = {ui.axH, S.pos(3, :), 'altitude (m)'; ui.axV, S.vel(3, :), 'vertical speed (m/s)'};
for i = 1:2
  a = tp{i, 1}; cla(a); plot(a, S.t, tp{i, 2}, 'LineWidth', 1.4); hold(a, 'on'); grid(a, 'on');
  ylabel(a, tp{i, 3}); xlim(a, [0 S.t(end)]);
  markEvents(a, S); ui.cur(i) = line([0 0], get(a, 'YLim'), 'Parent', a, 'Color', 'r'); hold(a, 'off');
end
a = ui.axA; cla(a);
plot(a, S.t, S.tilt(1, :), 'b', S.t, S.tilt(2, :), 'c', S.t, S.gim(1, :), 'r', S.t, S.gim(2, :), 'm', 'LineWidth', 1.1);
pk = max(max(abs([S.tilt(1:2, :); S.gim]))); yl = min(60, max(10, ceil(pk / 5) * 5 + 5));
hold(a, 'on'); grid(a, 'on'); xlim(a, [0 S.t(end)]); ylim(a, [-yl yl]); xlabel(a, 'time (s)');
ylabel(a, 'deg'); title(a, 'tilt X (blue)  tilt Y (cyan)  gimbal X (red)  gimbal Y (magenta)', 'FontWeight', 'normal', 'FontSize', 8);
markEvents(a, S); ui.cur(3) = line([0 0], [-yl yl], 'Parent', a, 'Color', 'r'); hold(a, 'off');

set(ui.res, 'String', resultText(S, P));
set(fig, 'UserData', ui);
end

function markEvents(a, S)
yl = get(a, 'YLim');
if ~isnan(S.tApo), line([S.tApo S.tApo], yl, 'Parent', a, 'Color', [0.5 0.5 0.5], 'LineStyle', '--'); end
if ~isnan(S.tCmd), line([S.tIgn2 S.tIgn2], yl, 'Parent', a, 'Color', [1 0.5 0], 'LineStyle', '--'); end
end

function txt = resultText(S, P)
vz = S.touchVel(3); vh = norm(S.touchVel(1:2)); sp = norm(S.touchVel);
if ~S.landed
  verdict = 'did not land within 45 s';
elseif S.chuteMode
  verdict = sprintf('CHUTE LANDING at %.1f m/s', sp);
elseif isnan(S.tCmd) || S.tIgn2 > S.t(end)
  verdict = 'CRASH - landing motor never lit before impact (shorter delay)';
elseif sp < 1.5 && S.touchTilt < 10
  verdict = 'SOFT LANDING - legs easily survive';
elseif sp < 3 && S.touchTilt < 15
  verdict = 'FIRM LANDING - legs should survive';
elseif sp < 6
  verdict = 'HARD LANDING - leg/tube damage likely';
else
  verdict = 'CRASH';
end
hint = '';
if ~S.chuteMode && S.landed && ~isnan(S.tCmd)
  tb = S.t(end) - S.tIgn2;
  if sp < 3, hint = 'This delay is in the sweet spot (+/- 0.01 s matters!)';
  elseif tb < 3.45, hint = sprintf('hit the ground %.1f s into the burn -> try a SHORTER delay', tb);
  else, hint = sprintf('burnt out %.1f s before touchdown -> try a LONGER delay', tb - 3.45); end
end
txt = { ...
  sprintf('RESULT: %s', verdict), ...
  sprintf('Apogee %.1f m at t = %.2f s | max tilt on ascent %.1f deg | max gimbal %.1f deg', S.apogee, S.tApo, S.maxTiltAsc, S.maxGim), ...
  sprintf('Touchdown: vertical %.2f m/s, sideways %.2f m/s, tilt %.1f deg, %.1f m from pad', vz, vh, S.touchTilt, norm(S.pos(1:2, end))) };
if ~S.chuteMode && ~isnan(S.tCmd) && S.tIgn2 <= S.t(end)
  [~, ic] = min(abs(S.t - S.tIgn2));
  txt{end+1} = sprintf('Motor 2: commanded %.2f s after apogee, lit at %.1f m falling at %.1f m/s', ...
                       P.landDelay, S.pos(3, ic), -S.vel(3, ic));
  txt{end+1} = hint;
end
end

% =====================================================================================
function H = makeRocket(ax, s)
H.s = s; H.ax = ax;
r = 0.0381; zt = -0.40; Lt = 0.60; Ln = 0.15;             % body: tail at -0.40 m from CG
[X, Y, Z] = cylinder(r, 20); H.tube = {X, Y, zt + Z * Lt};
[X, Y, Z] = cylinder([r 0], 20); H.nose = {X, Y, zt + Lt + Z * Ln};
[X, Y, Z] = cylinder([0.012 0.020], 12); H.bell = {X, Y, -Z * 0.05};
[X, Y, Z] = cylinder([0.018 0], 12); H.flame = {X, Y, Z};
H.zt = zt; H.r = r;
H.hTube  = surface(X*0, X*0, X*0, 'Parent', ax, 'FaceColor', [0.93 0.93 0.95], 'EdgeColor', 'none');
H.hNose  = surface(X*0, X*0, X*0, 'Parent', ax, 'FaceColor', [0.95 0.45 0.10], 'EdgeColor', 'none');
H.hBell  = surface(X*0, X*0, X*0, 'Parent', ax, 'FaceColor', [0.25 0.25 0.28], 'EdgeColor', 'none');
H.hFlame = surface(X*0, X*0, X*0, 'Parent', ax, 'FaceColor', [1.0 0.70 0.10], 'EdgeColor', 'none', 'FaceAlpha', 0.8);
for i = 1:4, H.hLeg(i) = line([0 0], [0 0], [0 0], 'Parent', ax, 'Color', [0.15 0.15 0.15], 'LineWidth', 2); end
[X, Y, Z] = sphere(16); Z(Z < 0) = NaN;
H.canopy = {X * 0.45, Y * 0.45, Z * 0.25 + 1.6};
H.hChute = surface(X*0, X*0, X*0, 'Parent', ax, 'FaceColor', [0.90 0.20 0.20], 'EdgeColor', 'none', 'Visible', 'off');
end

function setSurf(h, C, R, p, s)
sz = size(C{1});
P3 = R * [C{1}(:)'; C{2}(:)'; C{3}(:)'] * s;
set(h, 'XData', reshape(P3(1, :) + p(1), sz), 'YData', reshape(P3(2, :) + p(2), sz), 'ZData', reshape(P3(3, :) + p(3), sz));
end

function placeRocket(H, p, q, gim, T, legs, chute)
R = q2R(q); s = H.s;
setSurf(H.hTube, H.tube, R, p, s);
setSurf(H.hNose, H.nose, R, p, s);
% gimballed nozzle + flame (exhaust points opposite the thrust vector)
ga = gim * pi / 180; fb = [-sin(ga(2)); sin(ga(1)); 1]; fb = fb / norm(fb);
Rg = alignZ(-fb); pg = p + R * [0; 0; H.zt] * s;
setSurf(H.hBell, {H.bell{1}, H.bell{2}, -H.bell{3}}, R * Rg, pg, s);
if T > 0.5
  Lf = 0.08 + 0.35 * T / 25;
  setSurf(H.hFlame, {H.flame{1}, H.flame{2}, 0.05 + H.flame{3} * Lf}, R * Rg, pg, s);
  set(H.hFlame, 'Visible', 'on');
else
  set(H.hFlame, 'Visible', 'off');
end
% legs: stowed along the tube, 35 deg out when released
for i = 1:4
  a = pi/4 + (i - 1) * pi/2; d = [cos(a); sin(a); 0];
  hinge = H.zt + 0.22; ang = 35 * pi / 180 * legs;
  foot = [0; 0; hinge] + H.r * d + 0.26 * (sin(ang) * d - cos(ang) * [0; 0; 1]);
  pts = p + R * [[0; 0; hinge] + H.r * d, foot] * s;
  set(H.hLeg(i), 'XData', pts(1, :), 'YData', pts(2, :), 'ZData', pts(3, :));
end
if chute
  setSurf(H.hChute, H.canopy, eye(3), p, s); set(H.hChute, 'Visible', 'on');
else
  set(H.hChute, 'Visible', 'off');
end
end

function R = alignZ(v)     % rotation taking +z onto unit vector v
v = v / norm(v); z = [0; 0; 1]; c = z' * v; ax = cross(z, v); sn = norm(ax);
if sn < 1e-9, R = eye(3) * sign(c + (c == 0)); return; end
ax = ax / sn; K = [0 -ax(3) ax(2); ax(3) 0 -ax(1); -ax(2) ax(1) 0];
R = eye(3) + sn * K + (1 - c) * K * K;
end

function drawFrame(fig, k)
ui = get(fig, 'UserData'); S = ui.sim;
p = S.pos(:, k); q = S.q(:, k);
placeRocket(ui.hOver, p, q, S.gim(:, k), S.T(k), S.legs(k), S.chute(k));
placeRocket(ui.hChase, p, q, S.gim(:, k), S.T(k), S.legs(k), S.chute(k));
if p(3) < 3                                          % near the ground: widen the view to include it
  hz = (p(3) + 1.0) / 2; zc = hz - 0.05;
else
  hz = 0.8; zc = p(3) + 0.05;
end
set(ui.axC, 'XLim', p(1) + [-hz hz], 'YLim', p(2) + [-hz hz], 'ZLim', zc + [-hz hz]);
for i = 1:3, set(ui.cur(i), 'XData', S.t(k) * [1 1]); end
names = {'on the rail', 'BOOST (TVC on)', 'coast', 'falling', 'LANDING BURN (TVC on)', 'under chute', 'touchdown'};
title(ui.axC, sprintf('t = %5.2f s   alt %5.1f m   v %5.1f m/s   %s', S.t(k), p(3), S.vel(3, k), names{S.phase(k) + 1}));
set(ui.slider, 'Value', (k - 1) / max(1, numel(S.t) - 1));
drawnow;
end

function animate(fig)
ui = get(fig, 'UserData'); S = ui.sim;
sp = [0.25 0.5 1 2 4]; sp = sp(get(ui.speed, 'Value'));
t0 = tic; k = 1; N = numel(S.t);
while k <= N
  if ~ishandle(fig), return; end
  drawFrame(fig, k);
  tw = toc(t0) * sp;                                 % skip frames if drawing is slow
  k = max(k + 1, find(S.t >= tw, 1));
  if isempty(k), k = N + 1; end
  lag = S.t(min(k, N)) / sp - toc(t0);
  if lag > 0, pause(lag); end
end
drawFrame(fig, N);
end

% =====================================================================================
function R = selfTest(varargin)
% headless check: rocketSim3D('selftest')  -> runs chute + landing flights, prints results
P.kp = 0.30; P.ki = 0.05; P.kd = 0.08; P.gimMax = 5; P.servoTau = 0.03; P.servoRate = 150;
P.landDelay = 1.76; P.ignDelay = 0.35; P.mass = 1.00; P.len = 0.70; P.cgGimbal = 0.30;
P.cpOffset = 0.05; P.cd = 0.60; P.wind = 2.0; P.gust = 0.5; P.railAngle = 3; P.misalign = 0.5;
P.seed = 1; P.chuteMode = false; P.noise = true; P.diam = 0.0762;
for i = 1:2:numel(varargin), P.(varargin{i}) = varargin{i+1}; end
R = simulateFlight(P, 0.001, 20);
t = resultText(R, P); fprintf('%s\n', t{:});
end
