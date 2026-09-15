function export_lab_corpus(toolbox, destination, original)
  pkg load image;
  addpath(toolbox);
  candidates=load(fullfile(destination,'candidates.mat'));
  before=load(fullfile(original,'inputs.mat'));
  search_lab=reshape(rgb2lab(reshape(candidates.search,[],1,3)),[],3);
  scaled=search_lab(:,1)*2.55;
  indices=[]; selected_k=[]; selected_side=[]; distances=[]; missing=[];
  exact_ties=find(scaled-floor(scaled)==0.5);
  for k=0:254
    delta=scaled-(k+0.5);
    for side=[-1,1]
      eligible=find(delta*side>0 & abs(delta)<=0.001);
      if isempty(eligible)
        missing=[missing; k side];
      else
        [distance,j]=min(abs(delta(eligible)));
        indices(end+1)=eligible(j); selected_k(end+1)=k;
        selected_side(end+1)=side; distances(end+1)=distance;
      end
    end
  end
  selection=struct('pool_indices_one_based',indices,'k',selected_k,'side',selected_side, ...
    'distance',distances,'missing_k_side',missing,'exact_tie_pool_indices',exact_ties, ...
    'selected_scaled_l',scaled(indices),'maximum_distance',0.001);
  fid=fopen(fullfile(destination,'boundary_selection.json'),'w');
  fprintf(fid,'%s\n',jsonencode(selection)); fclose(fid);
  inputs=[before.inputs {reshape(candidates.dark,[],1,3), ...
    reshape(candidates.random,[],1,3),reshape(candidates.search(indices,:),[],1,3)}];
  names={'palette','structured','gray_ramp','dark','random','boundaries'};
  for k=1:numel(inputs)
    rgb=inputs{k}; lab=rgb2lab(rgb); hsv=rgb2hsv(rgb);
    l_work=uint8(lab(:,:,1)*2.55); v_work=uint8(hsv(:,:,3)*255);
    lab_work=lab; lab_work(:,:,1)=scale2lum(l_work,2);
    hsv_work=hsv; hsv_work(:,:,3)=scale2lum(v_work,1);
    lab_processed=lab; lab_processed(:,:,1)=scale2lum(max(l_work,uint8(128)),2);
    hsv_processed=hsv; hsv_processed(:,:,3)=scale2lum(max(v_work,uint8(128)),1);
    lab_roundtrip=lab2rgb(lab); hsv_roundtrip=hsv2rgb(hsv);
    lab_work_rgb=lab2rgb(lab_work); hsv_work_rgb=hsv2rgb(hsv_work);
    lab_processed_rgb=lab2rgb(lab_processed); hsv_processed_rgb=hsv2rgb(hsv_processed);
    lab_roundtrip_u8=uint8(lab_roundtrip*255); hsv_roundtrip_u8=uint8(hsv_roundtrip*255);
    lab_work_u8=uint8(lab_work_rgb*255); hsv_work_u8=uint8(hsv_work_rgb*255);
    lab_processed_u8=uint8(lab_processed_rgb*255); hsv_processed_u8=uint8(hsv_processed_rgb*255);
    save('-mat7-binary',fullfile(destination,[names{k} '.mat']), ...
      'rgb','lab','hsv','l_work','v_work','lab_work','hsv_work','lab_processed','hsv_processed', ...
      'lab_roundtrip','hsv_roundtrip','lab_work_rgb','hsv_work_rgb','lab_processed_rgb','hsv_processed_rgb', ...
      'lab_roundtrip_u8','hsv_roundtrip_u8','lab_work_u8','hsv_work_u8','lab_processed_u8','hsv_processed_u8');
    fprintf('%s: %d pixels\n',names{k},numel(l_work));
  end
  palette_lab=rgb2lab(before.inputs{1}); palette_lab=reshape(palette_lab,[],3);
  perturbed=[];
  for offset=[-0.001,0,0.001]
    item=palette_lab; item(:,1)+=offset; perturbed=[perturbed; item];
  end
  lab=[candidates.gamut_grid; perturbed; candidates.neutral_lab];
  rgb=lab2rgb(lab); rgb_u8=uint8(rgb*255);
  save('-mat7-binary',fullfile(destination,'inverse.mat'),'lab','rgb','rgb_u8');
  rgb_break=repmat((0.04045+[-1e-12;0;1e-12]),1,3);
  xyz_break=repmat(((6/29)^3+[-1e-12;0;1e-12]),1,3).*[0.95047,1,1.08883];
  linear_break=repmat((0.0031308+[-1e-12;0;1e-12]),1,3);
  inverse_matrix=[3.240479,-1.537150,-0.498535;-0.969256,1.875992,0.041556;0.055648,-0.204043,1.057311];
  companding_xyz=linear_break/inverse_matrix';
  rgb_break_xyz=rgb2xyz(rgb_break); xyz_break_lab=xyz2lab(xyz_break);
  companding_rgb=xyz2rgb(companding_xyz);
  save('-mat7-binary',fullfile(destination,'conventions.mat'),'rgb_break','xyz_break','linear_break', ...
    'companding_xyz','rgb_break_xyz','xyz_break_lab','companding_rgb');
  packages=pkg('list'); image_version='';
  for k=1:numel(packages)
    if strcmp(packages{k}.name,'image'), image_version=packages{k}.version; end
  end
  sources=struct();
  for name={'rgb2xyz','xyz2lab','lab2xyz','xyz2rgb','rgb2lab','lab2rgb','rgb2hsv','hsv2rgb'}
    sources.(name{1})=struct('path',which(name{1}),'sha256',hash('sha256',fileread(which(name{1}))));
  end
  manifest=struct('octave',version(),'image',image_version,'computer',computer(), ...
    'reference_commit','870e058fe8bf1e4090baf2401ff0e127d1c0237a', ...
    'generator','reference/octave/export_lab_corpus.m','generator_version',1, ...
    'generator_sha256',hash('sha256',fileread(which('export_lab_corpus'))), ...
    'generated_utc',strftime('%Y-%m-%dT%H:%M:%SZ',gmtime(time())), ...
    'boundary_count',numel(indices),'inverse_count',rows(lab),'sources',sources);
  fid=fopen(fullfile(destination,'octave_manifest.json'),'w');
  fprintf(fid,'%s\n',jsonencode(manifest)); fclose(fid);
end
