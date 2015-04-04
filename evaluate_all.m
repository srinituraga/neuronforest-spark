for expt = {'2015-04-02 15-27-28', ...
            '2015-04-06 12-31-04', ...
            '2015-04-06 14-04-13', ...
            '2015-04-06 17-59-35', ...
            '2015-04-02 00-47-01', ...
            '2015-04-02 00-47-01', ...
            '2015-04-01 23-34-27', ...
            '2015-04-05 14-54-08', ...
            '2015-04-05 16-01-43'
            }
    dir1 = ['/masters_predictions/' expt{1} '/predictions'];
    files1 = dir(dir1);
    for i = 3:length(files1)
        partial = files1(i).name;
        dir2 = [dir1 '/' partial];
        files2 = dir(dir2);
        for j = 3:length(files2)           
            depth = files2(j).name;
            dir3 = [dir2 '/' depth];
            files3 = dir(dir3);
            for k = 3:length(files3)
                trainortest = files3(k).name;
                root = [dir3 '/' trainortest];
                 if(exist([root '/errors_new.mat'], 'file') == 2)
                    fprintf([root ' already evaluated. ignoring\n']);
                 else
                    description = fileread([root '/0/description.txt']);
                    fprintf('\nExperiment: %s\n', root);
                    files4 = dir(root);
                    a = {};
                    for l=3:length(files4)
                        if(files4(l).isdir)
                            a = [a [root '/' files4(l).name]];
                        end
                    end
                    dims = get_dimensions(a);
                    evaluate_predictions(a, dims, description)
                 end
            end
        end
    end
end