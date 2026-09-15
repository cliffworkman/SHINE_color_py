function export_hsv_corpus(destination)
  pkg load image;
  c=load(fullfile(destination,'candidates.mat'));
  rgb=c.rgb; hsv=reshape(rgb2hsv(reshape(rgb,[],1,3)),[],3);
  working_v=uint8(hsv(:,3)*255);
  native=hsv2rgb(hsv); terminal=uint8(native*255);
  save('-mat7-binary',fullfile(destination,'forward.mat'),'rgb','hsv','working_v','native','terminal');
  search_hsv=reshape(rgb2hsv(reshape(c.search,[],1,3)),[],3);
  indices=[]; processed=[]; selected_hsv=[]; selected_rgb=[]; selected_native=[];
  for v=c.processed_values
    modified=search_hsv; modified(:,3)=double(v)/255;
    native=hsv2rgb(modified); scaled=native*255;
    distance=abs(scaled-(floor(scaled)+0.5));
    selected=find(any(distance<=1e-10,2));
    indices=[indices;selected]; processed=[processed;repmat(v,numel(selected),1)];
    selected_hsv=[selected_hsv;modified(selected,:)];
    selected_rgb=[selected_rgb;c.search(selected,:)]; selected_native=[selected_native;native(selected,:)];
  end
  rgb=selected_rgb; hsv=selected_hsv; native=selected_native; terminal=uint8(native*255);
  save('-mat7-binary',fullfile(destination,'boundaries.mat'),'rgb','hsv','native','terminal','indices','processed');
  selection=struct('rule','any(abs(RGB*255-(floor(RGB*255)+0.5))<=1e-10)', ...
    'threshold',1e-10,'pool_size',rows(c.search),'count',rows(rgb), ...
    'processed_values',c.processed_values,'selected_before_python_comparison',true);
  fid=fopen(fullfile(destination,'selection.json'),'w'); fprintf(fid,'%s\n',jsonencode(selection)); fclose(fid);
  rgb=c.captured_rgb; hsv=reshape(rgb2hsv(reshape(rgb,[],1,3)),[],3);
  hsv(:,3)=double(c.captured_v(:))/255; native=hsv2rgb(hsv); terminal=uint8(native*255);
  save('-mat7-binary',fullfile(destination,'captured.mat'),'rgb','hsv','native','terminal');
  hsv=c.inverse; native=hsv2rgb(hsv); terminal=uint8(native*255);
  save('-mat7-binary',fullfile(destination,'inverse.mat'),'hsv','native','terminal');
  sources=struct();
  for name={'rgb2hsv','hsv2rgb'}
    sources.(name{1})=struct('path',which(name{1}),'sha256',hash('sha256',fileread(which(name{1}))));
  end
  manifest=struct('octave',version(),'image','2.18.2','computer',computer(), ...
    'planner',fftw('planner'),'threads',fftw('threads'),'wisdom_nonempty',!isempty(fftw('dwisdom')), ...
    'sources',sources,'generator_sha256',hash('sha256',fileread(which('export_hsv_corpus'))), ...
    'generated_utc',strftime('%Y-%m-%dT%H:%M:%SZ',gmtime(time())));
  fid=fopen(fullfile(destination,'octave_manifest.json'),'w'); fprintf(fid,'%s\n',jsonencode(manifest)); fclose(fid);
  disp(selection);
end
