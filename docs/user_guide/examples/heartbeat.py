import siliconcompiler                        # import python package
chip = siliconcompiler.Chip()                 # create chip object
chip.set('source', 'heartbeat.v')             # define list of source files
chip.set('design', 'heartbeat')               # set top module
chip.clock(name='clk', pin='clk', period=1.0) # define a clock
chip.target('asicflow_freepdk45')             # load predefined target
chip.run()                                    # run compilation
chip.summary()                                # print results summary
chip.show()                                   # show layout file
