/*
 * This file defines the Music Player component.
 */
import React from "react";
import {
  Grid,
  Typography,
  Card,
  IconButton,
  LinearProgress,
} from "@mui/material";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import SkipNextIcon from "@mui/icons-material/SkipNext";
import PauseIcon from "@mui/icons-material/Pause";
import axios from "axios";

/*
 * Render the MusicPlayer component.
 */
function MusicPlayer(props) {
  // Compute the progress through the song
  var songProgress = (props.time / props.duration) * 100;

  // Execute API request to backend to play a Song for a Room
  function playSong() {
    axios
      .put("/spotify/play")
      .then((response) => response.data)
      .then((data) => {
        console.log(data);
      })
      .catch((error) => {
        console.error("There was an error!", error);
      });
  }

  // Execute API request to backend to pause a Song for a Room
  function pauseSong() {
    axios
      .put("/spotify/pause")
      .then((response) => response.data)
      .then((data) => {
        console.log(data);
      })
      .catch((error) => {
        console.error("There was an error!", error);
      });
  }

  // Execute API request to backend to skip a Song for a Room
  function skipSong() {
    axios
      .put("/spotify/skip")
      .then((response) => response.data)
      .then((data) => {
        console.log(data);
      })
      .catch((error) => {
        console.error("There was an error!", error);
      });
  }

  return (
    <Card>
      <Grid contanier alignItems="center">
        <Grid item align="center" xs={4}>
          <img src={props.image_url} height="100%" width="100%" />
        </Grid>
        <Grid item align="center" xs={12}>
          <Typography component="h5" variant="h5">
            {props.title}
          </Typography>
          <Typography color="textSecondary" variant="subtitle1">
            {props.artist}
          </Typography>
          <div>
            <IconButton
              onClick={() => {
                props.is_playing ? pauseSong() : playSong();
              }}
            >
              {props.is_playing ? "Pause" : "Play"}
              {/* TODO: Bug causing error when trying to use mui icons */}
              {/* {props.is_playing ? <PauseIcon /> : <PlayArrowIcon />} */}
            </IconButton>
            <IconButton onClick={() => skipSong()}>
              {props.votes} / {props.votes_required} Skip
              {/* TODO: Bug causing error when trying to use mui icons */}
              {/* {props.votes} /{" "} {props.votes_required} <SkipNextIcon /> */}
            </IconButton>
          </div>
        </Grid>
      </Grid>
      <LinearProgress variant="determinate" value={songProgress} />
    </Card>
  );
}

export default MusicPlayer;
