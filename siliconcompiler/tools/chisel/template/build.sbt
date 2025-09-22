// Based on https://github.com/chipsalliance/chisel-template/blob/main/build.sbt

ThisBuild / scalaVersion     := "2.13.14"

val chiselVersion = "3.6.1"

Compile / scalaSource := baseDirectory.value / "inputs"

lazy val root = (project in file("."))
  .settings(
    libraryDependencies ++= Seq(
      "edu.berkeley.cs" %% "chisel3" % chiselVersion,
      "org.scalatest" %% "scalatest" % "3.2.16" % "test",
    ),
    scalacOptions ++= Seq(
      "-language:reflectiveCalls",
      "-deprecation",
      "-feature",
      "-Xcheckinit",
      "-Ymacro-annotations",
    ),
    addCompilerPlugin("edu.berkeley.cs" %% "chisel3-plugin" % chiselVersion cross CrossVersion.full),
  )

// Prevents exception on exit
trapExit := false
