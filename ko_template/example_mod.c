#include <linux/init.h>
#include <linux/module.h>

static int __init example_init(void){
  printk(KERN_INFO "Example: staring...");
  // stuff to do
  printk(KERN_INFO "Example: staring done.");
  return 0;
}

static void __exit example_exit(void){
  printk(KERN_INFO "Example: stopping...");
  // stuff to do
  printk(KERN_INFO "Example: stopping done.");
}

module_init(example_init);
module_exit(example_exit);

