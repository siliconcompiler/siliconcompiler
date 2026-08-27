/* Stands in for the testbench soda-opt writes next to the kernel it outlines.
   Its name is what matters here -- bambu is what reads the contents. */
#include <stdio.h>

extern void main_kernel(void);

int main(void)
{
    main_kernel();
    return 0;
}
