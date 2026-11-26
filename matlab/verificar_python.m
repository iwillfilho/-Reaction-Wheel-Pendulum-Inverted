%VERIFICAR_PYTHON Confere o MATLAB contra a simulação em Python do repositório.
%   Lê referencia_python.json (gerado por `python -m sim.export_matlab`) e
%   compara parâmetros derivados, matrizes A e B, ganhos das três leis e as
%   trajetórias em malha fechada. Termina com erro se alguma coisa não bater.

aqui = fileparts(mfilename('fullpath'));
ref = jsondecode(fileread(fullfile(aqui, 'referencia_python.json')));
p = rwp_params();
g = rwp_projeto(p);
[A, B] = rwp_linear(p);
falhas = 0;

fprintf('Parâmetros derivados\n');
for c = fieldnames(ref.derivados)'
    campo = c{1};
    falhas = falhas + ~confere(campo, p.(campo), ref.derivados.(campo), 1e-12);
end
fprintf('Modelo linear\n');
falhas = falhas + ~confere('A', A, ref.A, 1e-12);
falhas = falhas + ~confere('B', B, ref.B, 1e-12);
fprintf('Ganhos\n');
falhas = falhas + ~confere('K (LQR)', g.K, ref.ganhos.K, 1e-6);
falhas = falhas + ~confere('KI (LQI)', g.KI, ref.ganhos.KI, 1e-6);
falhas = falhas + ~confere('kp, ki, kd (PID)', [g.kp g.ki g.kd], [ref.ganhos.kp ref.ganhos.ki ref.ganhos.kd], 1e-12);

fprintf('Malha fechada (solto a %.0f°, peteleco de %.1f rad/s em %.1f s)\n', ...
    ref.ensaio.theta0_graus, ref.ensaio.disturbio(2), ref.ensaio.disturbio(1));
for lei = {'lqr', 'lqi', 'pid'}
    tr = ref.trajetorias.(lei{1});
    r = rwp_simular(p, g, lei{1}, 'theta0', deg2rad(ref.ensaio.theta0_graus), 'T', ref.ensaio.T, ...
        'disturbios', ref.ensaio.disturbio(:)');
    idx = 1:ref.ensaio.passo:numel(r.t);
    eth = max(abs(r.theta(idx) - tr.theta));
    eom = max(abs(r.omega(idx) - tr.omega));
    ok = eth < 1e-6 && eom < 1e-4;
    fprintf('  %-4s  |theta| %.1e rad   |omega| %.1e rad/s  %s\n', upper(lei{1}), eth, eom, rotulo(ok));
    if ~ok, falhas = falhas + 1; end
end

if falhas
    error('verificar_python:falhou', '%d comparações não bateram com o Python.', falhas);
end
fprintf('\nTudo igual ao Python.\n');

function ok = confere(nome, mat, py, tol)
% erro relativo máximo entre o valor do MATLAB e o do Python
e = max(abs(mat(:) - py(:)) ./ max(abs(py(:)), 1e-12));
ok = e < tol;
fprintf('  %-34s erro relativo %.1e  %s\n', nome, e, rotulo(ok));
end

function s = rotulo(ok)
if ok, s = 'ok'; else, s = 'FALHOU'; end
end
