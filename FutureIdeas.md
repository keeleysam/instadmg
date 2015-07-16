This is a scratch pad for ideas for the future of InstaDMG.

# Introduction #

When adding ideas please leave your handle and explain the idea well.

# Details #

  * karl.kuehn: ~~Redo the dmg mounting portion to allow for multiple dmg's to be mounted and for individual pkg's to be used from them with their own installerchoices files. Possibly do this with a single "union" mount to make the multiple DVD's look like one disk and be able to hide it from the finder.~~ Moved to the roadmap.

  * karl.kuehn: Transform the BaseOS cache images from Read/Write to compressed to save ourselves a number of Gigs.

  * karl.kuehn: ~~Put in a method of installing applications that do drag-and-drop install. This would be far easier if InstaDMG and InstaUp2Date merge. Then it would simply be a type like dmg and folder are now. As a temporary hack, we could move anything that is a .app into the applications folder.~~ Moved to the roadmap.

  * karl.kuehn: Re-work the BaseOS disk manipulation. Allow for http mounts, and make sure that things get un-mounted at the end.

  * karl.kuehn: Add trap code to catch when someone Control-C's out and clean up a lot of error handling code.

  * joshwisenbaker: ~~Transition code to Python~~ Moved to the roadmap.

  * joshwisenbaker: SIU integration via automator

  * karl.kuehn: ~~use update\_dyld\_shared\_cache -root -universal\_boot to re-create the shared cache for faster booting. The negative of this would be that every computer would have the same "random" addresses.~~ consensus is that it is not worth it