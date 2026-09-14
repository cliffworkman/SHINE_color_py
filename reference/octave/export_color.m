function export_color(toolbox, destination)
  pkg load image;
  addpath(toolbox);
  f=load(fullfile(destination,'inputs.mat'));
  records=cell(size(f.inputs));
  for k=1:numel(f.inputs)
    rgb=f.inputs{k};
    hsv=rgb2hsv(rgb); lab=rgb2lab(rgb);
    v_work=uint8(hsv(:,:,3)*255); l_work=uint8(lab(:,:,1)*2.55);
    v_native=scale2lum(v_work,1); l_native=scale2lum(l_work,2);
    v_processed=max(v_work,uint8(128)); l_processed=max(l_work,uint8(128));
    hsv_work=hsv; hsv_work(:,:,3)=v_native;
    lab_work=lab; lab_work(:,:,1)=l_native;
    hsv_processed=hsv; hsv_processed(:,:,3)=scale2lum(v_processed,1);
    lab_processed=lab; lab_processed(:,:,1)=scale2lum(l_processed,2);
    r=struct('rgb',rgb,'hsv',hsv,'lab',lab,'v_work',v_work,'l_work',l_work, ...
      'v_native',v_native,'l_native',l_native,'v_processed',v_processed,'l_processed',l_processed, ...
      'hsv_roundtrip',hsv2rgb(hsv),'lab_roundtrip',lab2rgb(lab), ...
      'hsv_work_native',hsv_work,'lab_work_native',lab_work, ...
      'hsv_processed_native',hsv_processed,'lab_processed_native',lab_processed, ...
      'hsv_work_rgb',hsv2rgb(hsv_work),'lab_work_rgb',lab2rgb(lab_work), ...
      'hsv_processed_rgb',hsv2rgb(hsv_processed),'lab_processed_rgb',lab2rgb(lab_processed));
    records{k}=r;
  end
  save('-mat7-binary',fullfile(destination,'octave.mat'),'records');
  packages=pkg('list'); image_version='';
  for k=1:numel(packages)
    if strcmp(packages{k}.name,'image'), image_version=packages{k}.version; end
  end
  manifest=struct('octave',version(),'image',image_version,'computer',computer(), ...
    'reference_commit','870e058fe8bf1e4090baf2401ff0e127d1c0237a', ...
    'generator','reference/octave/export_color.m','generator_version',1, ...
    'generator_sha256',hash('sha256',fileread(which('export_color'))), ...
    'generated_utc',strftime('%Y-%m-%dT%H:%M:%SZ',gmtime(time())), ...
    'rgb2hsv_source',which('rgb2hsv'),'rgb2lab_source',which('rgb2lab'));
  fid=fopen(fullfile(destination,'octave_manifest.json'),'w');
  fprintf(fid,'%s\n',jsonencode(manifest)); fclose(fid);
end
