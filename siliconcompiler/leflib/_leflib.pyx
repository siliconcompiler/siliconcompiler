# from libc.stdio cimport FILE, fopen, fclose

# cdef extern from "lefrReader.hpp":
#     int lefrInit()

def parse(path):
    # if lefrInit() != 0:
    #     return None

    #  f_ptr = fopen(path, 'r')
    #  if f_ptr == 0:
    #      print("Couldn't open file " + path)
    #      return None

    #  r = lefrRead(f_ptr, path, NULL)

    #  fclose(f_ptr)

    return "SUCCESS"
