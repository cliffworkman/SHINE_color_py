function export_reference_fixtures(toolbox, destination, reference_sha)
  % Fixtures call the unmodified repaired toolbox. No algorithm source copied.
  pkg load image;
  pkg load datatypes;
  addpath(toolbox);
  if ~exist(destination, 'dir'), mkdir(destination); end
  manifest = struct('octave_version', version(), 'reference_commit', reference_sha, ...
    'reference_branch', 'main', 'generated_utc', strftime('%Y-%m-%dT%H:%M:%SZ', gmtime(time())), ...
    'script', 'reference/octave/export_reference_fixtures.m', ...
    'operations', {{'uint8', 'rescale', 'lumMatch', 'avgHist', 'hist2list', 'histMatch', 'sfMatch', 'specMatch'}}, ...
    'colorspace', 'synthetic 0-255 single channels');
  manifest.fft_environment = fft_environment();
  packages = pkg('list');
  manifest.packages = struct();
  for k = 1:numel(packages)
    if any(strcmp(packages{k}.name, {'image', 'datatypes'}))
      manifest.packages.(packages{k}.name) = packages{k}.version;
    end
  end
  cast_input = [-Inf NaN -1 -0.5 0 0.49 0.5 1.5 2.5 127.5 254.49 254.5 255 256 Inf];
  cast_output = uint8(cast_input);
  save('-mat7-binary', fullfile(destination, 'numeric.mat'), 'cast_input', 'cast_output');
  shapes = [6 8; 5 7; 5 8; 8 5; 16 18];
  for s = 1:rows(shapes)
    h = shapes(s,1); w = shapes(s,2);
    [x,y] = meshgrid(0:w-1, 0:h-1);
    inputs = {uint8(mod(17*x+31*y+7*x.*y,256)), ...
              uint8(mod(43*x+11*y+3*x.^2+29,256)), ...
              uint8(mod(5*x+61*y+13*y.^2+83,256))};
    for k = 1:numel(inputs)
      imwrite(inputs{k}, fullfile(destination, sprintf('channel_%dx%d_%d.png',h,w,k)));
    end
    rescale1 = rescale(inputs,1); rescale2 = rescale(inputs,2);
    luminance = lumMatch(inputs);
    means = cellfun(@mean2, inputs); sample_sds = cellfun(@std2, inputs);
    constant_inputs = {inputs{1}, uint8(ones(h,w)*73), inputs{3}};
    constant_luminance = lumMatch(constant_inputs);
    input_histograms = cellfun(@imhist, inputs, 'UniformOutput', false);
    target_histogram = avgHist(inputs);
    target_values = hist2list(target_histogram);
    histogram_output = histMatch(inputs,0);
    output_histograms = cellfun(@imhist, histogram_output, 'UniformOutput', false);
    histogram_means = cellfun(@mean2, histogram_output);
    histogram_sds = cellfun(@std2, histogram_output);
    % Independent standard FFT diagnostics; these are not intercepted locals.
    spectra = cellfun(@(a) fftshift(fft2(double(a)/255)), inputs, 'UniformOutput', false);
    amplitudes = cellfun(@abs, spectra, 'UniformOutput', false);
    phases = cellfun(@angle, spectra, 'UniformOutput', false);
    target_amplitude = mean(cat(3,amplitudes{:}),3);
    sf_outputs = cell(1,3); spec_outputs = cell(1,3);
    for option = 0:2
      sf_outputs{option+1} = sfMatch(inputs, option);
      spec_outputs{option+1} = specMatch(inputs, option);
    end
    save('-mat7-binary',fullfile(destination,sprintf('primitives_%dx%d.mat',h,w)), ...
      'inputs','rescale1','rescale2','luminance','means','sample_sds', ...
      'constant_inputs','constant_luminance','input_histograms','target_histogram', ...
      'target_values','output_histograms','histogram_means','histogram_sds', ...
      'spectra','amplitudes','phases','target_amplitude','sf_outputs','spec_outputs');
  end
  probe_edge_cases(toolbox,destination);
  fid = fopen(fullfile(destination,'manifest.json'),'w');
  fprintf(fid,'%s\n',jsonencode(manifest)); fclose(fid);
end
