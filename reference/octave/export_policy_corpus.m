function export_policy_corpus(toolbox, data, cache, phase)
  % Separate conditioning and final-output phases. No SHINE source duplicated.
  pkg load image;
  addpath(toolbox);
  if ~exist(cache,'dir'), mkdir(cache); end
  files=dir(fullfile(data,'*_inputs.mat'));
  manifest=struct('environment',fft_environment(),'reference_commit', ...
    '870e058fe8bf1e4090baf2401ff0e127d1c0237a','phase',phase, ...
    'generated_utc',strftime('%Y-%m-%dT%H:%M:%SZ',gmtime(time())));
  for s=1:numel(files)
    name=strrep(files(s).name,'_inputs.mat','');
    f=load(fullfile(data,files(s).name)); inputs=f.inputs;
    if strcmp(phase,'conditioning')
      spectra=cellfun(@(a) fftshift(fft2(double(a)/255)),inputs,'UniformOutput',false);
      phases=cell(size(inputs)); amplitudes=phases;
      for k=1:numel(inputs)
        [phases{k},amplitudes{k}]=cart2pol(real(spectra{k}),imag(spectra{k}));
      end
      save('-mat7-binary',fullfile(cache,[name '_spectra.mat']),'spectra','phases','amplitudes');
    elseif strcmp(phase,'outputs')
      sf_outputs=cell(1,3); spec_outputs=cell(1,3);
      for option=0:2
        sf_outputs{option+1}=sfMatch(inputs,option);
        spec_outputs{option+1}=specMatch(inputs,option);
      end
      save('-mat7-binary',fullfile(cache,[name '_outputs.mat']),'sf_outputs','spec_outputs');
    else
      error('Unknown phase');
    end
    fprintf('%s %s complete\n',phase,name);
  end
  fid=fopen(fullfile(data,[phase '_octave_manifest.json']),'w');
  fprintf(fid,'%s\n',jsonencode(manifest)); fclose(fid);
end
