function output=pipeline_capture_call(name,varargin)
  global pipeline_original pipeline_stages pipeline_channel pipeline_iteration;
  input=varargin{1};
  output=pipeline_original.(name)(varargin{:});
  stage=struct('operation',name,'channel',pipeline_channel,'iteration',pipeline_iteration, ...
    'input',{input},'output',{output});
  if strcmp(name,'histMatch')
    stage.target_histogram=avgHist(input);
    stage.output_histograms=cellfun(@(a) imhist(a),output,'UniformOutput',false);
  end
  if strcmp(name,'sfMatch') || strcmp(name,'specMatch')
    stage.rescale_option=varargin{2};
    z=cellfun(@(a) fftshift(fft2(double(a)/255)),input,'UniformOutput',false);
    stage.amplitudes=cellfun(@(a) hypot(real(a),imag(a)),z,'UniformOutput',false);
    stage.phases=cellfun(@(a) atan2(imag(a),real(a)),z,'UniformOutput',false);
  end
  pipeline_stages{end+1}=stage;
end
