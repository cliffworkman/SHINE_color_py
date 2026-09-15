function export_pipeline(toolbox,destination)
  pkg load image;
  addpath(toolbox);
  global pipeline_original pipeline_stages pipeline_channel pipeline_iteration;
  pipeline_original=struct('lumMatch',@lumMatch,'histMatch',@histMatch,'sfMatch',@sfMatch,'specMatch',@specMatch);
  delegates=struct();
  for name=fieldnames(pipeline_original)'
    info=functions(pipeline_original.(name{1}));
    assert(strcmpi(info.file,fullfile(toolbox,[name{1} '.m'])));
    delegates.(name{1})=info.file;
  end
  wrappers=fullfile(fileparts(mfilename('fullpath')),'pipeline_capture');
  environment=fft_environment();
  addpath(wrappers,'-begin');
  unwind_protect
    assert(strcmpi(which('histMatch'),fullfile(wrappers,'histMatch.m')));
    files=dir(fullfile(destination,'*_inputs.mat'));
    for g=1:numel(files)
      source=load(fullfile(destination,files(g).name)); rgb=source.inputs;
      runs={};
      for cs=1:3
        parts=cell(3,numel(rgb));
        for i=1:numel(rgb)
          if cs==1, native=double(rgb{i});
          elseif cs==2, native=rgb2hsv(rgb{i});
          else, native=rgb2lab(rgb{i}); end
          for ch=1:3, parts{ch,i}=native(:,:,ch); end
          if cs==1
            for ch=1:3, parts{ch,i}=uint8(parts{ch,i}); end
          elseif cs==2, parts{3,i}=uint8(parts{3,i}*255);
          else, parts{1,i}=uint8(parts{1,i}*2.55); end
        end
        active=1:3; if cs==2, active=3; elseif cs==3, active=1; end
        for mode=1:8
          options=1; if mode>=3, options=0:2; end
          for iterations=1:2
            for option=options
              current=parts; pipeline_stages={};
              for it=1:iterations
                for ch=active
                  pipeline_channel=ch; pipeline_iteration=it;
                  text=evalc('result=processImage(current(ch,:),mode,1,[],[],0,option);');
                  current(ch,:)=result;
                end
              end
              native_rgb=cell(size(rgb)); terminal=cell(size(rgb));
              for i=1:numel(rgb)
                if cs==1
                  native_rgb{i}=double(cat(3,current{1,i},current{2,i},current{3,i}))/255;
                elseif cs==2
                  native_rgb{i}=hsv2rgb(cat(3,current{1,i},current{2,i},scale2lum(current{3,i},1)));
                else
                  native_rgb{i}=lab2rgb(cat(3,scale2lum(current{1,i},2),current{2,i},current{3,i}));
                end
                terminal{i}=uint8(native_rgb{i}*255);
              end
              assert(numel(pipeline_stages)==numel(active)*iterations*(1+(mode>=5)));
              runs{end+1}=struct('colorspace',cs,'mode',mode,'iterations',iterations,'rescale_option',option, ...
                'seed',{parts},'working',{current},'stages',{pipeline_stages},'native_rgb',{native_rgb},'terminal',{terminal});
            end
          end
        end
      end
      name=strrep(files(g).name,'_inputs.mat','');
      save('-mat7-binary',fullfile(destination,[name '_reference.mat']),'rgb','runs');
      fprintf('%s: %d configurations\n',name,numel(runs));
    end
  unwind_protect_cleanup
    rmpath(wrappers);
    clear global pipeline_original pipeline_stages pipeline_channel pipeline_iteration;
  end_unwind_protect
  info=struct('environment',environment,'reference_commit','870e058fe8bf1e4090baf2401ff0e127d1c0237a', ...
    'dispatcher','processImage','dispatcher_sha256',hash('sha256',fileread(fullfile(toolbox,'processImage.m'))), ...
    'delegates',delegates,'generator','reference/octave/export_pipeline.m','generator_version',1, ...
    'generated_utc',strftime('%Y-%m-%dT%H:%M:%SZ',gmtime(time())), ...
    'scope','External color/iteration harness with actual repaired processImage and unmodified public primitives; no SHINE_color filesystem/wizard shell');
  fid=fopen(fullfile(destination,'octave_manifest.json'),'w'); fprintf(fid,'%s\n',jsonencode(info)); fclose(fid);
end
