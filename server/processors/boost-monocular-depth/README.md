# Boosting Monocular Depth Estimation Models to High-Resolution via Content-Adaptive Multi-Resolution Merging

This processor estimates high resolution depth maps from single images using the code from [Miangoleh et. al.](https://github.com/compphoto/BoostingMonocularDepth).

Note the code's [license](https://github.com/compphoto/BoostingMonocularDepth/blob/main/LICENSE).

## Building The Container

```
 docker build --progress=plain -t boost-monocular-depth .
```

## Quickrun

Create two directories:
```
mkdir -p inputs outputs
```
and put the images you want to extract depth for in the `inputs` directory.

Next, mount the current directory to `/data` when calling the container:

```
docker run -it \
    -v $(pwd):/data \
    boost-monocular-depth
```

## Changing Options
You can see the full set of flags to change with:
```
docker run -it boost-monocular-depth -h
```

## Runing in CPU Mode
NOTE: Using a CPU will take a _long time_ and a _lot of memory_ (like 8GB) to generate a depth image. But it's doable....

To use the cpu, simply pass `--gpu_ids -1` to the container.