function replay_fft_stages(toolbox, destination)
  % Standard inverse FFT and public rescale calls on Python-captured inputs.
  addpath(toolbox);
  old_planner = fftw('planner'); old_threads = fftw('threads');
  unwind_protect
    fftw('planner','estimate'); fftw('threads',1);
    loaded = load(fullfile(destination,'python_stage_inputs.mat'));
    traces = loaded.traces;
    for k = 1:numel(traces)
      t = traces{k};
      t.octave_raw = cellfun(@(a) real(ifft2(a)),t.inverse_inputs,'UniformOutput',false);
      t.octave_outputs = cell(1,3);
      t.octave_outputs{1} = cellfun(@(a) uint8(a*255),t.octave_raw,'UniformOutput',false);
      t.octave_outputs{2} = rescale(t.octave_raw,1);
      t.octave_outputs{3} = rescale(t.octave_raw,2);
      % Isolate scaling from inverse FFT by also scaling Python's exact raw data.
      t.octave_scaling_python_raw = {rescale(t.python_raw,1),rescale(t.python_raw,2)};
      traces{k} = t;
    end
    nan_inputs = loaded.nan_inputs;
    nan_outputs = {rescale(nan_inputs,1),rescale(nan_inputs,2)};
    save('-mat7-binary',fullfile(destination,'octave_stage_replay.mat'),'traces','nan_inputs','nan_outputs');
  unwind_protect_cleanup
    fftw('planner',old_planner); fftw('threads',old_threads);
  end_unwind_protect
  assert(strcmp(fftw('planner'),old_planner) && fftw('threads')==old_threads);
end
