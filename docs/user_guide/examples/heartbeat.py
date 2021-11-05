import siliconcompiler                        # import python package

chip = siliconcompiler.Chip()                 # create chip object
chip.add('source', 'heartbeat.v')             # define list of source files
chip.set('design', 'heartbeat')               # set top module
chip.clock(name='clk', pin='clk', period=1.0) # define a clock
chip.target('asicflow_freepdk45')             # load builtin compiler settings
#remote_server = 'server.siliconcompiler.com'  # remote server address
#chip.set('remote','addr', remote_server)      # specify name of remote server
#chip.set('remote','user', '<signup email>')   # userid
#chip.set('remote','password','<password>')    # password
chip.run()                                    # run compilation
chip.summary()                                # print results summary
