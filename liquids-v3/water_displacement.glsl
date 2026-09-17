  if (fluid_kind == 2) {
    // Reconstruct world space after skinning, then deform the real water mesh.
    vec4 clip=gl_Position;
    clip.y /= (512.0/416.0)*0.5;
    vec4 reconstructed=inverse(-pc_camera)*clip;
    vec3 P=reconstructed.xyz/reconstructed.w/4096.0+cam_trans.xyz/4096.0;
    float height=0.0;
    for(int i=0;i<32;i++) {
      float age=fluid_time-fluid_contacts[i].w;
      if(fluid_strength[i]<=0.0 || age<0.0 || age>4.0 || abs(P.y-fluid_contacts[i].y)>0.45)continue;
      float d=length(P.xz-fluid_contacts[i].xz);
      float q=d-(0.10+age*1.40);
      float width=0.19+age*0.12;
      height+=fluid_strength[i]*cos(q*13.0)*exp(-q*q/(width*width)-age*1.15);
    }
    P.y+=clamp(height,-0.16,0.16);
    gl_Position=-pc_camera*vec4(P*4096.0-cam_trans.xyz,1.0);
    gl_Position.y *= (512.0/416.0)*0.5;
  }
