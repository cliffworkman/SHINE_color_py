function info = fft_environment()
  % Non-mutating provenance. A nonempty wisdom header need not contain plans.
  info = struct('octave_version', version(), 'computer', computer(), ...
    'planner', fftw('planner'), 'threads', fftw('threads'));
  wisdom = fftw('dwisdom');
  info.wisdom_nonempty = ~isempty(wisdom);
  info.wisdom_length = numel(wisdom);
  info.wisdom_sha256 = hash('sha256', wisdom);
  info.wisdom_has_plan_entries = ~isempty(regexp(wisdom, '\(fftw_[^\s]+_register', 'once'));
  token = regexp(wisdom, '^\(fftw-([^\s]+)', 'tokens', 'once');
  info.fftw_version = token{1};
end
