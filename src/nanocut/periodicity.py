import numpy as np
from .output import error
__all__ = [ "Periodicity", ]


def gcd(a, b, c):
    """Calculates greatest common divisor of three numbers."""
    while b:
        a, b = b, a % b
    while c:
        a, c = c, a % c
    return a


class Periodicity:
    """Holds information about type of periodicity, and axes.
    
    Attributes:
        period_type: Type of the periodicity ("0D", "1D" or "2D")
        axis: Axis vector(s) in relatvie coordinates.
        axis_cart: Axis vector(s) in cartesian coordinates.
    """

    def __init__(self, geometry, period_type, axis=None):
        """Initialized Periodicity instance.
        
        Args:
            geometry: Geometry object to provide transformation.
            period_type: Periodicity type ("0D", "1D", "2D").
            axis: (3, -1) array with periodicity vectors.
        """
        self.period_type = period_type
        if self.period_type not in [ "0D", "1D", "2D" ]:
            raise ValueError("Value of period_type is invalid.")
        if self.period_type == "0D":
            self.axis = None
            self.axis_cart = None
            return
        axis = np.array(axis, dtype=int)
        axis.shape = (-1, 3)
        if self.period_type == "1D":
            self._axis = axis / gcd(axis[0,0], axis[0,1], axis[0,2])
        elif self.period_type == "2D":
            gcd1 = gcd(axis[1,0], axis[1,1], axis[1,2])
            gcd0 = gcd(axis[0,0], axis[0,1], axis[0,2])
            self._axis = np.vstack(( axis[1] / gcd1, axis[0] / gcd0 ))
        self._axis_cart = geometry.coord_transform(self._axis, "lattice")


    def rotate_coordsys(self, atoms_coords):
        """Rotates coordinate system to have standardized z-axis.
        
        Args:
            atom_coords: Cordinate to rotate.
            
        Returns:
            Rotated coordinates. For 0D systems it returns the original
            coordinates. For 1D systems periodicity will be along the z-axis,
            for 2D sytems z-axis will be orthogonal to the periodic directions
            and the first lattice vector will be along the x-axis.
        """
        if self.period_type == "1D":
            z_axis = self._axis_cart[0]
        elif self.period_type == "2D":
            z_axis = np.cross(self._axis_cart[0], self._axis_cart[1])
        elif self.period_type == "0D":
            return "", atoms_coords
        z_axis= z_axis / np.linalg.norm(z_axis)
        # Calculate rotation angle
        angle = np.arccos(np.dot(z_axis, np.array([0,0,1])))
        # Calculate rotation axis
        rot = np.cross(z_axis, np.array([0,0,1]))
        norm = np.linalg.norm(rot)
        if norm > 1e-12:
            rot /= norm
        sin = np.sin(angle)
        cos = np.cos(angle)
        # Calculate rotation matrix
        rotation_matrix = np.array([
            [ cos + rot[0] * rot[0] * (1 - cos),
             rot[1] * rot[0] * (1 - cos) + rot[2] * sin,
             rot[2] * rot[0] * (1 - cos) - rot[1] * sin ],  
            [ rot[0] * rot[1] * (1 - cos)- rot[2] * sin, 
             cos + rot[1] * rot[1] * (1 - cos),
             rot[2] * rot[1] * (1-cos) + rot[0] * sin, ],
            [ rot[0] * rot[2] * (1 - cos) + rot[1] * sin,
             rot[1] * rot[2] * (1 - cos) - rot[0] * sin,
             cos + rot[2] * rot[2] * (1 - cos) ]])
        # Rotate atoms
        atoms_coords = np.dot(atoms_coords, rotation_matrix)
        # Calculate rotated axes and write them to string
        axis_string = "Periodicity axes: "
        for axis in np.dot(self._axis_cart, rotation_matrix):
            axis_string += ("(" + repr(axis[0]) + ", " + repr(axis[1]) + ", "
                            + repr(axis[2]) + ") ")
        return axis_string, atoms_coords


    def get_axis(self,coordsys="lattice"):
        """Returns axis.
        
        Args:
            coordsys: Coordinate system type ("lattice" or "cartesian").
            
        Returns:
            Periodicity axis in the given coordinate system.
        """
        if self.period_type == "1D" or self.period_type == "2D":
            if coordsys == "lattice":
                return self._axis
            elif coordsys == "cartesian":
                return self._axis_cart
            else:
                raise ValueError("Value of coordsys is invalid.")
        else:
            raise ValueError("get_axis() called, but period_type is not 1D"
                             " or 2D.")


    def arrange_positions(self, geometry, atoms_coords, atoms_idx):
        """Folds atoms in the central unit cell, with relative coordinates
        between 0.0 and 1.0.
        
        Args:
            geometry: geometry object.
            atoms_coords: Cartesian coordinates of the atoms.
            atoms_idx: Type of the atoms.
            
        Returns:
            Cartesian coordinates of the atoms in the unit cell.
        """
        '''Put atoms in periodic structures in proper position'''
        if self.period_type == "1D":    
            axis_norm = np.linalg.norm(self._axis_cart[0])
            shifts = np.floor(
                        np.dot(atoms_coords, np.transpose(self._axis_cart[0]))
                        / axis_norm**2)
            atoms_coords -= shifts[:,np.newaxis] * self._axis_cart[0]
        elif self.period_type == "2D":
            axis_3D = np.array([ self._axis_cart[0], self._axis_cart[1],
                                np.cross(self._axis[0], self._axis_cart[1]) ]) 
            invbasis = np.linalg.inv(axis_3D)
            shifts = np.floor(np.dot(atoms_coords, invbasis))
            shifts[:,2] = 0.0
            atoms_coords -= np.dot(shifts, axis_3D)


    @classmethod
    def fromdict(cls, geometry, inidict):
        """Builds instance from dictionary."""

        try:
            section = inidict["periodicity"]
        except KeyError:
            return cls(geometry, "0D")
        
        period_type = section.get("period_type","0D")
        if period_type == "0D":
            return cls(geometry, "0D")

        elif period_type == "1D":
            axis = section.get("axis", None)
            if axis is None:
                error("Missing axis specification.")
            try:
                axis = np.array([ int(s) for s in axis.split() ])
                axis.shape = (1, 3)
            except ValueError:
                error("Invalid axis specification.")
            if np.all(axis == 0):
                exit("Invalid axis direction.")
            return cls(geometry, "1D", axis)

        elif period_type == "2D":
            axis = section.get("axis", None)
            if axis is None:
                error("Missing axis specification.")
            try:
                axis = np.array([ int(s) for s in axis.split() ])
                axis.shape = (2, 3)
            except ValueError:
                error("Invalid axis specification.")
            if np.all(axis[0] == 0) or np.all(axis[1] == 0):
                error("Invalid axis directons.")
            if np.all(np.cross(axis[0], axis[1]) == 0):
                error("Axis are parallel.")
            return cls(geometry, "2D", axis)
