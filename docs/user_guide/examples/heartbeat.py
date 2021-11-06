import siliconcompiler                        # import python package

chip = siliconcompiler.Chip()                 # create chip object
chip.add('source', 'heartbeat.v')             # define list of source files
chip.set('design', 'heartbeat')               # set top module
chip.clock(name='clk', pin='clk', period=1.0) # define a clock
chip.target('asicflow_freepdk45')             # load builtin compiler settings
#chip.set('remote', True)                     # runs compilation remotely
chip.run()                                    # run compilation
chip.summary()                                # print results summary
#chip.show_file()                             # show layout file
