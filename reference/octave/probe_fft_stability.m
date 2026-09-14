function probe_fft_stability(toolbox, fixtures, destination)
  % Calls the unchanged reference. Outputs are separate from frozen fixtures.
  pkg load image;
  addpath(toolbox);
  if ~exist(destination,'dir'), mkdir(destination); end
  prior = fft_environment();
  prior_wisdom = fftw('dwisdom');
  prior_swisdom = fftw('swisdom');
  manifest = struct('before',prior,'reference_commit', ...
    '870e058fe8bf1e4090baf2401ff0e127d1c0237a', ...
    'generated_utc',strftime('%Y-%m-%dT%H:%M:%SZ',gmtime(time())), ...
    'script','reference/octave/probe_fft_stability.m');
  runs = struct([]);
  files = dir(fullfile(fixtures,'primitives_*.mat'));
  configurations = {'default', prior.planner, prior.threads; ...
                    'estimate_1', 'estimate', 1; ...
                    'measure_1', 'measure', 1};
  unwind_protect
    for c = 1:rows(configurations)
      name = configurations{c,1};
      record = struct('name',name,'error','');
      try
        if c > 1
          fftw('planner',configurations{c,2});
          fftw('threads',configurations{c,3});
          % Isolate controlled plans from wisdom accumulated in prior runs.
          fftw('dwisdom','');
        end
        record.before = fft_environment();
        run_dir = fullfile(destination,name);
        if ~exist(run_dir,'dir'), mkdir(run_dir); end
        for s = 1:numel(files)
          old = load(fullfile(fixtures,files(s).name));
          inputs = old.inputs;
          normalized = cellfun(@(a) double(a)/255,inputs,'UniformOutput',false);
          spectra = cellfun(@(a) fftshift(fft2(a)),normalized,'UniformOutput',false);
          phases = cell(size(inputs)); amplitudes = phases;
          for k = 1:numel(inputs)
            [phases{k},amplitudes{k}] = cart2pol(real(spectra{k}),imag(spectra{k}));
          end
          sf_outputs = cell(1,3); spec_outputs = cell(1,3);
          sf_repeat = cell(1,3); spec_repeat = cell(1,3);
          for option = 0:2
            sf_outputs{option+1} = sfMatch(inputs,option);
            spec_outputs{option+1} = specMatch(inputs,option);
            sf_repeat{option+1} = sfMatch(inputs,option);
            spec_repeat{option+1} = specMatch(inputs,option);
          end
          repeated_spectra = cellfun(@(a) fftshift(fft2(a)),normalized,'UniformOutput',false);
          save('-mat7-binary',fullfile(run_dir,files(s).name), ...
            'inputs','normalized','spectra','amplitudes','phases', ...
            'sf_outputs','spec_outputs','sf_repeat','spec_repeat','repeated_spectra');
        end
        record.after = fft_environment();
      catch err
        record.error = err.message;
      end
      runs(c) = record;
    end
  unwind_protect_cleanup
    fftw('planner',prior.planner);
    fftw('threads',prior.threads);
    % Empty serialized wisdom headers need not be importable on all builds.
    % Clearing already restores them exactly; only import if still different.
    fftw('dwisdom','');
    if ~strcmp(fftw('dwisdom'),prior_wisdom), fftw('dwisdom',prior_wisdom); end
    % No single-precision transforms or wisdom mutations occurred in this probe.
    manifest.after_restore = fft_environment();
    manifest.single_precision_wisdom_unchanged = strcmp(fftw('swisdom'),prior_swisdom);
    manifest.restored = strcmp(fftw('planner'),prior.planner) && ...
      fftw('threads') == prior.threads && strcmp(fftw('dwisdom'),prior_wisdom);
    manifest.runs = runs;
    fid = fopen(fullfile(destination,'octave_environment.json'),'w');
    fprintf(fid,'%s\n',jsonencode(manifest)); fclose(fid);
  end_unwind_protect
  assert(manifest.restored);
end
