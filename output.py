# -*- coding: utf-8 -*-
'''
Created on Sep 2, 2009

@author: sebastian
'''
import numpy

def write_structure_to_file(geometry, atoms, test, file):
  fi = open(file, 'w')
  
  fi.write(repr(sum(test)) + '\n\n')
  for idx in range(len(atoms)):
    if test[idx] == True:
      fi.write(geometry._basis_names[int(atoms[idx][3])] +' '+repr(atoms[idx][0])\
               +' '+ repr(atoms[idx][1])+' '+ repr(atoms[idx][2])+'\n')
  fi.close()